from __future__ import annotations

import asyncio
import json
import os
import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.cognition import (
    merge_retrieval_results,
    record_message,
    retrieve_lexical,
    retrieve_semantic,
)
from aurora.core import event_envelope, settings
from aurora.gateway import ReasoningError, ReasoningGateway
from aurora.quorum import Contribution, compare_contributions, should_deliberate, synthesis_prompt

router = APIRouter(prefix="/v1", tags=["cognition"])
bearer = HTTPBearer(auto_error=False)
bearer_dependency = Depends(bearer)


class ClaimReviewRequest(BaseModel):
    workspace_id: uuid.UUID
    status: str = Field(pattern="^(unverified|supported|contested|rejected|superseded)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = Field(default=None, max_length=5000)


class QuorumRequest(BaseModel):
    workspace_id: uuid.UUID
    question: str = Field(min_length=1, max_length=10000)
    session_id: uuid.UUID | None = None
    models: list[str] | None = None
    mode: str = Field(default="quorum", pattern="^(quorum|deep)$")


@router.post("/claims/{claim_id}/review")
def review_claim(
    claim_id: uuid.UUID,
    request: ClaimReviewRequest,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> dict:
    """Thin adapter; the database function owns revision and temporal semantics."""
    from apps.api.main import current_user

    user_id = current_user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        member = conn.execute(
            "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
            (request.workspace_id, user_id),
        ).fetchone()
        if not member:
            raise HTTPException(403, "User is not a member of this workspace")
        claim = conn.execute(
            "select 1 from public.claims where id=%s and workspace_id=%s",
            (claim_id, request.workspace_id),
        ).fetchone()
        if not claim:
            raise HTTPException(404, "Claim not found")
        try:
            belief_id = conn.execute(
                "select public.revise_claim(%s,%s,%s,%s::numeric,%s)",
                (claim_id, request.status, user_id, request.confidence, request.rationale),
            ).fetchone()[0]
            conn.commit()
        except psycopg.Error as exc:
            conn.rollback()
            raise HTTPException(409, "Claim revision could not be applied") from exc
    return {
        "claim_id": str(claim_id),
        "status": request.status,
        "belief_id": str(belief_id) if belief_id else None,
        "reviewed_by": str(user_id),
    }


def _quorum_models(requested: list[str] | None) -> list[str]:
    if requested:
        return requested[:3]
    configured = [item.strip() for item in os.getenv("AURORA_QUORUM_MODELS", "").split(",") if item.strip()]
    if configured:
        return configured[:3]
    return [settings.default_model] if settings.default_model else []


@router.post("/quorum")
async def quorum(
    request: QuorumRequest,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> dict:
    """Selective multi-model deliberation; every model remains an attributed contributor."""
    from apps.api.main import current_user

    user_id = current_user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    correlation_id = uuid.uuid4()
    session_id = request.session_id or uuid.uuid4()
    models = _quorum_models(request.models)
    if not models:
        raise HTTPException(503, "No QUORUM models configured")
    gateway = ReasoningGateway()

    with psycopg.connect(settings.database_url) as conn:
        member = conn.execute(
            "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
            (request.workspace_id, user_id),
        ).fetchone()
        if not member:
            raise HTTPException(403, "User is not a member of this workspace")
        if request.session_id:
            session = conn.execute(
                "select 1 from public.sessions where id=%s and workspace_id=%s and user_id=%s",
                (session_id, request.workspace_id, user_id),
            ).fetchone()
            if not session:
                raise HTTPException(404, "Session not found")
        else:
            conn.execute(
                "insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,%s)",
                (session_id, request.workspace_id, user_id, request.question[:100]),
            )
        _, user_event_id = record_message(
            conn, workspace_id=request.workspace_id, session_id=session_id,
            role="user", content=request.question, source_id=None, correlation_id=correlation_id,
        )
        lexical = retrieve_lexical(conn, workspace_id=request.workspace_id, question=request.question)
        semantic: list[dict] = []
        if settings.openai_api_key or settings.openrouter_api_key:
            try:
                embedding_result = await gateway.embed([request.question])
                semantic = retrieve_semantic(
                    conn, workspace_id=request.workspace_id,
                    embedding=embedding_result["embeddings"][0], limit=8,
                )
            except ReasoningError:
                semantic = []
        retrieved = merge_retrieval_results(lexical, semantic, limit=8)
        context = [{"content": item["content"], "evidence_id": item["evidence_id"]} for item in retrieved]
        contradiction_count = conn.execute(
            "select count(*) from public.claim_contradictions(%s)", (request.workspace_id,)
        ).fetchone()[0]
        warranted, warrant_reason = should_deliberate(
            mode=request.mode,
            evidence_count=len(retrieved),
            contradiction_count=contradiction_count,
        )
        if not warranted:
            raise HTTPException(400, "QUORUM was not warranted by the selected mode")

        results = await asyncio.gather(
            *(gateway.reason(question=request.question, context=context, model=model, mode="quorum") for model in models),
            return_exceptions=True,
        )
        evidence_ids = tuple(str(item["evidence_id"]) for item in retrieved if item.get("evidence_id"))
        contributions = []
        failures = []
        successful_results = []
        for model, result in zip(models, results):
            if isinstance(result, Exception):
                failures.append({"model": model, "error": str(result)})
                continue
            successful_results.append(result)
            contributions.append(
                Contribution(
                    model_id=result["model"],
                    provider=result.get("provider"),
                    response=result["answer"],
                    confidence=result.get("confidence"),
                    evidence_ids=evidence_ids,
                )
            )
        if not contributions:
            raise HTTPException(502, "All QUORUM contributors failed")
        deliberation = compare_contributions(request.question, contributions)
        synthesis = await gateway.reason(
            question=request.question,
            context=[{"content": synthesis_prompt(request.question, deliberation), "evidence_id": "quorum-deliberation"}],
            model=settings.default_model,
            mode="quorum",
        )
        reasoning_run_id = uuid.uuid4()
        metadata = {
            "correlation_id": str(correlation_id), "quorum": True,
            "warrant_reason": warrant_reason, "requested_models": models,
            "failed_models": failures, "agreement": deliberation.agreement,
            "evidence_coverage": deliberation.evidence_coverage,
            "collective_gain": deliberation.collective_gain,
            "disagreements": deliberation.disagreements,
        }
        conn.execute(
            """insert into public.reasoning_runs
            (id,workspace_id,session_id,question,mode,status,answer,confidence,started_at,completed_at,metadata)
            values (%s,%s,%s,%s,'quorum','completed',%s,%s,%s,%s,%s::jsonb)""",
            (reasoning_run_id, request.workspace_id, session_id, request.question,
             synthesis["answer"], synthesis.get("confidence"), synthesis["started_at"],
             synthesis["completed_at"], json.dumps(metadata)),
        )
        for contribution, result in zip(contributions, successful_results):
            conn.execute(
                """insert into public.model_contributions
                (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids)
                values (%s,%s,%s,'quorum_contributor',%s,%s,%s,%s,%s)""",
                (reasoning_run_id, contribution.model_id, contribution.provider, contribution.response,
                 contribution.confidence, result.get("latency_ms"), result.get("estimated_cost"), list(evidence_ids)),
            )
        conn.execute(
            """insert into public.model_contributions
            (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids)
            values (%s,%s,%s,'quorum_synthesis',%s,%s,%s,%s,%s)""",
            (reasoning_run_id, synthesis["model"], synthesis.get("provider"), synthesis["answer"],
             synthesis.get("confidence"), synthesis.get("latency_ms"), synthesis.get("estimated_cost"), list(evidence_ids)),
        )
        _, assistant_event_id = record_message(
            conn, workspace_id=request.workspace_id, session_id=session_id, role="assistant",
            content=synthesis["answer"], source_id=None, correlation_id=correlation_id,
        )
        event = event_envelope(
            event_type="quorum.completed", producer_type="model", producer_id=None,
            workspace_id=str(request.workspace_id), session_id=str(session_id),
            causation_id=str(user_event_id), correlation_id=str(correlation_id), payload=metadata,
        )
        conn.execute(
            """insert into public.events
            (id,workspace_id,session_id,event_type,producer_type,producer_id,event_time,recorded_at,
             causation_id,correlation_id,aggregate_type,aggregate_id,schema_version,payload)
            values (%(id)s,%(workspace_id)s,%(session_id)s,%(event_type)s,%(producer_type)s,%(producer_id)s,
                    %(event_time)s,%(recorded_at)s,%(causation_id)s,%(correlation_id)s,'reasoning_run',
                    %(aggregate_id)s,1,%(payload)s::jsonb)""",
            {**event, "aggregate_id": str(reasoning_run_id), "payload": json.dumps(event["payload"])},
        )
        conn.commit()
    return {
        "session_id": str(session_id), "reasoning_run_id": str(reasoning_run_id),
        "answer": synthesis["answer"], "evidence": retrieved,
        "evidence_ids": list(evidence_ids),
        "contributions": [
            {"model": c.model_id, "provider": c.provider, "response": c.response,
             "confidence": c.confidence, "evidence_ids": list(c.evidence_ids)} for c in contributions
        ],
        "failures": failures,
        "deliberation": {
            "agreement": deliberation.agreement,
            "disagreements": list(deliberation.disagreements),
            "evidence_coverage": deliberation.evidence_coverage,
            "collective_gain": deliberation.collective_gain,
        },
        "trace": {"correlation_id": str(correlation_id), "user_event_id": str(user_event_id), "assistant_event_id": str(assistant_event_id)},
    }
