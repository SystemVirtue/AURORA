# ruff: noqa
from __future__ import annotations

import json
import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.cognition import merge_retrieval_results, record_message, retrieve_lexical
from aurora.core import event_envelope, settings
from aurora.quorum import Contribution, compare_contributions

router = APIRouter(prefix="/v1", tags=["puter"])
bearer = HTTPBearer(auto_error=False)


class PuterContribution(BaseModel):
    model: str = Field(min_length=1, max_length=300)
    provider: str | None = Field(default="puter", max_length=100)
    response: str = Field(min_length=1, max_length=100000)
    latency_ms: int | None = Field(default=None, ge=0, le=600000)


class PuterSynthesis(BaseModel):
    model: str = Field(min_length=1, max_length=300)
    response: str = Field(min_length=1, max_length=100000)
    latency_ms: int | None = Field(default=None, ge=0, le=600000)


class PuterAskRequest(BaseModel):
    workspace_id: uuid.UUID
    question: str = Field(min_length=1, max_length=10000)
    session_id: uuid.UUID | None = None
    mode: str = Field(default="balanced", pattern="^(fast|balanced|deep|quorum)$")
    contributions: list[PuterContribution] = Field(min_length=1, max_length=3)
    synthesis: PuterSynthesis | None = None


def _user(credentials: HTTPAuthorizationCredentials | None) -> uuid.UUID:
    from apps.api.main import current_user

    return current_user(credentials)


@router.post("/ask/puter")
def ask_puter(
    request: PuterAskRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """Persist a browser-executed Puter.js reasoning result."""
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    if request.mode in {"quorum", "deep"} and request.synthesis is None:
        raise HTTPException(422, "QUORUM/deep Puter reasoning requires a synthesis result")

    correlation_id = uuid.uuid4()
    session_id = request.session_id or uuid.uuid4()
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
        retrieved = merge_retrieval_results(lexical, [], limit=8)
        evidence_ids = tuple(str(item["evidence_id"]) for item in retrieved if item.get("evidence_id"))
        contributions = tuple(
            Contribution(model_id=item.model, provider=item.provider, response=item.response, evidence_ids=evidence_ids)
            for item in request.contributions
        )
        deliberation = compare_contributions(request.question, contributions) if len(contributions) > 1 else None
        answer = request.synthesis.response if request.synthesis else request.contributions[0].response
        answer_model = request.synthesis.model if request.synthesis else request.contributions[0].model
        reasoning_run_id = uuid.uuid4()
        metadata = {
            "correlation_id": str(correlation_id), "execution": "browser", "provider_mode": "puter_user_pays",
            "retrieval": retrieved, "evidence_ids": list(evidence_ids),
        }
        if deliberation:
            metadata["quorum"] = {
                "agreement": deliberation.agreement, "disagreements": deliberation.disagreements,
                "evidence_coverage": deliberation.evidence_coverage, "collective_gain": deliberation.collective_gain,
                "synthesis_model": answer_model,
            }
        conn.execute(
            """insert into public.reasoning_runs
            (id,workspace_id,session_id,question,mode,status,answer,confidence,started_at,completed_at,metadata)
            values (%s,%s,%s,%s,%s,'completed',%s,%s,now(),now(),%s::jsonb)""",
            (reasoning_run_id, request.workspace_id, session_id, request.question,
             "quorum" if deliberation else request.mode, answer, None, json.dumps(metadata, default=str)),
        )
        for item in request.contributions:
            conn.execute(
                """insert into public.model_contributions
                (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (reasoning_run_id, item.model, item.provider or "puter", "quorum_contributor" if deliberation else "reasoner",
                 item.response, None, item.latency_ms, 0, list(evidence_ids)),
            )
        if request.synthesis:
            conn.execute(
                """insert into public.model_contributions
                (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids)
                values (%s,%s,%s,'synthesizer',%s,%s,%s,%s,%s)""",
                (reasoning_run_id, request.synthesis.model, "puter", request.synthesis.response,
                 None, request.synthesis.latency_ms, 0, list(evidence_ids)),
            )
        _, assistant_event_id = record_message(
            conn, workspace_id=request.workspace_id, session_id=session_id, role="assistant",
            content=answer, source_id=None, correlation_id=correlation_id,
        )
        if not retrieved:
            conn.execute(
                "insert into public.epistemic_gaps (workspace_id,reasoning_run_id,description,gap_type,severity,status) values (%s,%s,%s,'missing_evidence',0.8,'open')",
                (request.workspace_id, reasoning_run_id, "No matching workspace evidence was retrieved."),
            )
        event = event_envelope(
            event_type="reasoning.completed", producer_type="model", producer_id=None,
            workspace_id=str(request.workspace_id), session_id=str(session_id),
            causation_id=str(user_event_id), correlation_id=str(correlation_id),
            payload={"execution": "browser", "provider": "puter", "model": answer_model,
                     "evidence_ids": list(evidence_ids), "assistant_event_id": str(assistant_event_id)},
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
        "answer": answer, "evidence": retrieved, "evidence_ids": list(evidence_ids),
        "model": answer_model, "provider": "puter", "execution": "browser", "provider_mode": "puter_user_pays",
        "quorum": {
            "contributors": [item.model_dump() for item in request.contributions], "synthesis_model": answer_model,
            "agreement": deliberation.agreement if deliberation else None,
            "disagreements": list(deliberation.disagreements) if deliberation else [],
            "evidence_coverage": deliberation.evidence_coverage if deliberation else (1.0 if retrieved else 0.0),
            "collective_gain": deliberation.collective_gain if deliberation else 0.0,
        } if deliberation else None,
        "trace": {"correlation_id": str(correlation_id), "user_event_id": str(user_event_id), "assistant_event_id": str(assistant_event_id)},
    }


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=300)
    preferences: dict = Field(default_factory=dict)


class CredentialUpdate(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    secret: str | None = Field(default=None, max_length=20000)
    metadata: dict = Field(default_factory=dict)


@router.get("/profile")
def get_profile(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("insert into public.user_profiles (user_id) values (%s) on conflict (user_id) do nothing", (user_id,))
        row = conn.execute("select display_name, timezone, default_model, preferences from public.user_profiles where user_id=%s", (user_id,)).fetchone()
        creds = conn.execute("select provider, label, metadata, secret_id is not null from public.user_credentials where user_id=%s order by provider, label", (user_id,)).fetchall()
        conn.commit()
    return {"user_id": str(user_id), "profile": {"display_name": row[0], "timezone": row[1], "default_model": row[2], "preferences": row[3] or {}}, "credentials": [{"provider": r[0], "label": r[1], "metadata": r[2], "configured": bool(r[3])} for r in creds], "openrouter": {"configured": bool(settings.openrouter_api_key), "source": "server_env" if settings.openrouter_api_key else "user_profile"}}


@router.patch("/profile")
def update_profile(request: ProfileUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("insert into public.user_profiles (user_id) values (%s) on conflict (user_id) do nothing", (user_id,))
        conn.execute("update public.user_profiles set display_name=%s, timezone=%s, default_model=%s, preferences=%s::jsonb, updated_at=now() where user_id=%s", (request.display_name, request.timezone, request.default_model, json.dumps(request.preferences), user_id))
        conn.commit()
    return {"ok": True}


@router.put("/profile/credentials")
def upsert_profile_credential(request: CredentialUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        existing = conn.execute("select id, secret_id from public.user_credentials where user_id=%s and provider=%s and label=%s", (user_id, request.provider, request.label)).fetchone()
        secret_id = existing[1] if existing else None
        if request.secret:
            if secret_id:
                conn.execute("select vault.update_secret(%s,%s,%s,%s)", (secret_id, request.secret, f"aurora:{user_id}:{request.provider}:{request.label}", "AURORA user credential"))
            else:
                secret_id = conn.execute("select vault.create_secret(%s,%s,%s)", (request.secret, f"aurora:{user_id}:{request.provider}:{request.label}", "AURORA user credential")).fetchone()[0]
        if existing:
            conn.execute("update public.user_credentials set secret_id=coalesce(%s,secret_id), metadata=%s::jsonb, updated_at=now() where id=%s", (secret_id, json.dumps(request.metadata), existing[0]))
        else:
            conn.execute("insert into public.user_credentials (user_id,provider,label,secret_id,metadata) values (%s,%s,%s,%s,%s::jsonb)", (user_id, request.provider, request.label, secret_id, json.dumps(request.metadata)))
        conn.commit()
    return {"ok": True, "provider": request.provider, "label": request.label, "configured": bool(secret_id)}


@router.delete("/profile/credentials/{provider}/{label}")
def delete_profile_credential(provider: str, label: str, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("delete from public.user_credentials where user_id=%s and provider=%s and label=%s", (user_id, provider, label))
        conn.commit()
    return {"ok": True}
