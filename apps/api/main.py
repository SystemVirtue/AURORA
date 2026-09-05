from __future__ import annotations

import json
import os
import uuid
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aurora.claims import persist_candidate_claims
from aurora.cognition import (
    record_message,
    retrieve_lexical,
    retrieve_semantic,
    merge_retrieval_results,
)
from aurora.core import settings
from aurora.gateway import ReasoningError, ReasoningGateway
from apps.api.continuity_routes import router as continuity_router
from apps.api.provenance_routes import router as provenance_router
from apps.api.revision_routes import router as revision_router

app = FastAPI(title="AURORA", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(revision_router)
app.include_router(provenance_router)
app.include_router(continuity_router)


class SessionRequest(BaseModel):
    workspace_id: uuid.UUID
    title: str | None = None


class DocumentRequest(BaseModel):
    workspace_id: uuid.UUID
    name: str
    content: str
    source_type: str = "document"


class AskRequest(BaseModel):
    workspace_id: uuid.UUID
    question: str
    session_id: uuid.UUID | None = None
    model: str | None = None
    mode: str = Field(default="balanced", pattern="^(fast|balanced|deep|quorum)$")



def current_user(authorization: Annotated[str | None, Header()] = None) -> uuid.UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    import jwt

    if not settings.supabase_jwt_secret:
        raise HTTPException(503, "SUPABASE_JWT_SECRET is not configured")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(401, "Invalid bearer token") from exc



def require_workspace_access(conn, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    row = conn.execute(
        "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
        (workspace_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(403, "Workspace access denied")



def require_session_access(conn, session_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    row = conn.execute(
        "select 1 from public.sessions where id=%s and workspace_id=%s and user_id=%s",
        (session_id, workspace_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Session not found")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "aurora-api"}


@app.get("/health/db")
def health_db() -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("select 1")
    return {"status": "ok", "database": "reachable"}


@app.post("/v1/sessions")
def create_session(request: SessionRequest, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        session_id = uuid.uuid4()
        conn.execute(
            "insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,%s)",
            (session_id, request.workspace_id, user_id, request.title or "AURORA session"),
        )
        conn.commit()
    return {"session_id": str(session_id)}


@app.post("/v1/documents")
def ingest_document(request: DocumentRequest, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        source_id = uuid.uuid4()
        document_id = uuid.uuid4()
        conn.execute(
            "insert into public.sources (id,workspace_id,source_type,title,metadata) values (%s,%s,%s,%s,%s::jsonb)",
            (source_id, request.workspace_id, request.source_type, request.name, json.dumps({"ingested_by": str(user_id)})),
        )
        conn.execute(
            "insert into public.documents (id,workspace_id,source_id,name,content) values (%s,%s,%s,%s,%s)",
            (document_id, request.workspace_id, source_id, request.name, request.content),
        )
        from aurora.cognition import chunk_text
        chunks = chunk_text(request.content)
        for index, content in enumerate(chunks):
            conn.execute(
                "insert into public.document_chunks (workspace_id,document_id,chunk_index,content,content_hash,token_estimate) values (%s,%s,%s,%s,%s,%s)",
                (request.workspace_id, document_id, index, content, __import__("hashlib").sha256(content.encode()).hexdigest(), len(content.split())),
            )
        event_id = uuid.uuid4()
        conn.execute(
            "insert into public.events (id,workspace_id,event_type,producer_type,producer_id,event_time,recorded_at,correlation_id,aggregate_type,aggregate_id,schema_version,payload) values (%s,%s,'document.ingested','human',%s,now(),now(),%s,'document',%s,1,%s::jsonb)",
            (event_id, request.workspace_id, user_id, event_id, document_id, json.dumps({"source_id": str(source_id), "name": request.name})),
        )
        claims = persist_candidate_claims(conn, request.workspace_id, document_id, request.content, event_id)
        conn.commit()
    return {"source_id": str(source_id), "document_id": str(document_id), "chunks": len(chunks), "candidate_claims": len(claims), "claim_status": "unverified"}



def _relevant_contradiction_count(conn, workspace_id: uuid.UUID, question: str) -> int:
    from aurora.claims import extract_claim_candidates
    terms = {word.lower().strip(".,?!:;()[]{}") for word in question.split() if len(word) > 2}
    if not terms:
        return 0
    rows = conn.execute(
        "select subject,predicate,object from public.claims where workspace_id=%s and assertion_status <> 'rejected'",
        (workspace_id,),
    ).fetchall()
    matched = []
    for row in rows:
        text = " ".join(str(value).lower() for value in row if value is not None)
        if terms & set(text.split()):
            matched.append(row)
    return len(matched) if len(matched) > 1 else 0


@app.post("/v1/ask")
async def ask(request: AskRequest, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    session_id = request.session_id or uuid.uuid4()
    correlation_id = uuid.uuid4()
    gateway = ReasoningGateway()
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        if request.session_id:
            require_session_access(conn, session_id, request.workspace_id, user_id)
        else:
            conn.execute("insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,%s)", (session_id, request.workspace_id, user_id, request.question[:100]))
        _, user_event_id = record_message(conn, workspace_id=request.workspace_id, session_id=session_id, role="user", content=request.question, source_id=None, correlation_id=correlation_id)
        lexical = retrieve_lexical(conn, workspace_id=request.workspace_id, question=request.question)
        semantic: list[dict] = []
        if settings.openai_api_key or settings.openrouter_api_key:
            try:
                embedding_result = await gateway.embed([request.question])
                semantic = retrieve_semantic(conn, workspace_id=request.workspace_id, embedding=embedding_result["embeddings"][0], limit=8)
            except ReasoningError:
                semantic = []
        retrieved = merge_retrieval_results(lexical, semantic, limit=8)
        context = [{"content": item["content"], "evidence_id": item.get("evidence_id")} for item in retrieved]
        contradiction_count = _relevant_contradiction_count(conn, request.workspace_id, request.question)
        warrant = "workspace_contradiction" if contradiction_count else ("missing_evidence" if not context else None)
        try:
            result = await gateway.reason(question=request.question, context=context, model=request.model, mode=request.mode, warrant=warrant)
        except ReasoningError as exc:
            raise HTTPException(502, str(exc)) from exc
        reasoning_run_id = uuid.uuid4()
        quorum = result.get("quorum")
        metadata = {"correlation_id": str(correlation_id), "retrieval": retrieved, "contradiction_count": contradiction_count, "warrant": quorum.get("warrant") if quorum else warrant}
        if quorum:
            metadata["quorum"] = quorum
        conn.execute("insert into public.reasoning_runs (id,workspace_id,session_id,question,mode,status,answer,confidence,started_at,completed_at,metadata) values (%s,%s,%s,%s,%s,'completed',%s,%s,%s,%s,%s::jsonb)", (reasoning_run_id, request.workspace_id, session_id, request.question, "quorum" if quorum else request.mode, result["answer"], result.get("confidence"), result["started_at"], result["completed_at"], json.dumps(metadata, default=str)))
        evidence_ids = [item["evidence_id"] for item in retrieved if item.get("evidence_id")]
        if quorum:
            for contributor in quorum["contributors"]:
                conn.execute("insert into public.model_contributions (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids) values (%s,%s,%s,'quorum_contributor',%s,%s,%s,%s,%s)", (reasoning_run_id, contributor["model"], contributor.get("provider"), contributor["response"], None, contributor.get("latency_ms"), None, contributor.get("evidence_ids", evidence_ids)))
            conn.execute("insert into public.model_contributions (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids) values (%s,%s,%s,'synthesizer',%s,%s,%s,%s,%s)", (reasoning_run_id, quorum["synthesis_model"], quorum.get("synthesis_provider"), result["answer"], result.get("confidence"), quorum.get("synthesis_latency_ms"), None, evidence_ids))
        else:
            conn.execute("insert into public.model_contributions (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids) values (%s,%s,%s,'reasoner',%s,%s,%s,%s,%s)", (reasoning_run_id, result["model"], result.get("provider"), result["answer"], result.get("confidence"), result.get("latency_ms"), result.get("estimated_cost"), evidence_ids))
        _, assistant_event_id = record_message(conn, workspace_id=request.workspace_id, session_id=session_id, role="assistant", content=result["answer"], source_id=None, correlation_id=correlation_id)
        if not retrieved:
            conn.execute("insert into public.epistemic_gaps (workspace_id,reasoning_run_id,description,gap_type,severity,status) values (%s,%s,%s,'missing_evidence',0.8,'open')", (request.workspace_id, reasoning_run_id, "No matching workspace evidence was retrieved."))
        reasoning_event_id = uuid.uuid4()
        conn.execute("insert into public.events (id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,correlation_id,aggregate_type,aggregate_id,schema_version,payload) values (%s,%s,%s,'reasoning.completed','model',%s,%s,%s,'reasoning_run',%s,1,%s::jsonb)", (reasoning_event_id, request.workspace_id, session_id, result["event_time"], result["event_time"], correlation_id, reasoning_run_id, json.dumps({"evidence_ids": evidence_ids, "assistant_event_id": str(assistant_event_id), "reasoning_run_id": str(reasoning_run_id)}, default=str)))
        quorum_event_id = None
        if quorum:
            quorum_event_id = uuid.uuid4()
            conn.execute("insert into public.events (id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,correlation_id,aggregate_type,aggregate_id,schema_version,payload) values (%s,%s,%s,'reasoning.quorum_completed','system',%s,%s,%s,'reasoning_run',%s,1,%s::jsonb)", (quorum_event_id, request.workspace_id, session_id, result["event_time"], result["event_time"], correlation_id, reasoning_run_id, json.dumps({"quorum": quorum}, default=str)))
        conn.commit()
    response = {"session_id": str(session_id), "reasoning_run_id": str(reasoning_run_id), "answer": result["answer"], "evidence": retrieved, "evidence_ids": evidence_ids, "model": result["model"], "provider": result.get("provider"), "latency_ms": result.get("latency_ms"), "trace": {"correlation_id": str(correlation_id), "user_event_id": str(user_event_id), "assistant_event_id": str(assistant_event_id), "warrant": quorum.get("warrant") if quorum else warrant}}
    if quorum:
        response["quorum"] = quorum
        response["trace"]["quorum_event_id"] = str(quorum_event_id)
    return response
