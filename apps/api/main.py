from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import jwt
import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.claims import extract_candidate_claims, persist_candidate_claims
from aurora.cognition import create_source_and_document, merge_retrieval_results, record_message, retrieve_lexical, retrieve_semantic
from aurora.core import event_envelope, settings
from aurora.gateway import ReasoningError, ReasoningGateway

app = FastAPI(title="AURORA", version="0.4.1")
bearer = HTTPBearer(auto_error=False)


class AskRequest(BaseModel):
    workspace_id: uuid.UUID
    question: str = Field(min_length=1, max_length=10000)
    session_id: uuid.UUID | None = None
    model: str | None = None
    mode: str = "balanced"


class DocumentRequest(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=2_000_000)
    mime_type: str = "text/plain"


class SessionRequest(BaseModel):
    workspace_id: uuid.UUID
    title: str | None = Field(default=None, max_length=500)


class ReindexRequest(BaseModel):
    workspace_id: uuid.UUID
    document_id: uuid.UUID | None = None
    batch_size: int = Field(default=32, ge=1, le=128)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> uuid.UUID:
    """Validate a Supabase JWT and return its immutable auth.users subject."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer authentication required")
    if not settings.supabase_jwt_secret:
        raise HTTPException(503, "SUPABASE_JWT_SECRET is not configured")
    try:
        payload = jwt.decode(credentials.credentials, settings.supabase_jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]}, leeway=10)
        user_id = uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return user_id


def require_workspace_access(conn, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    row = conn.execute("select 1 from public.workspace_members where workspace_id=%s and user_id=%s", (workspace_id, user_id)).fetchone()
    if not row:
        raise HTTPException(403, "User is not a member of this workspace")


def require_session_access(conn, session_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    row = conn.execute("""select 1 from public.sessions s join public.workspace_members wm on wm.workspace_id=s.workspace_id
        where s.id=%s and s.workspace_id=%s and wm.user_id=%s""", (session_id, workspace_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, "Session not found")


@app.get("/", include_in_schema=False)
def workspace_ui() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parents[1] / "web" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aurora-api"}


@app.get("/health/db")
def health_db() -> dict[str, str]:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("select 1")
    return {"status": "ok", "database": "reachable"}


@app.post("/v1/sessions")
def create_session(request: SessionRequest, user_id: uuid.UUID = Depends(current_user)) -> dict[str, str]:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    session_id = uuid.uuid4()
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        conn.execute("insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,%s)", (session_id, request.workspace_id, user_id, request.title))
        conn.commit()
    return {"session_id": str(session_id)}


@app.post("/v1/documents")
def ingest_document(request: DocumentRequest, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        source_id, document_id = create_source_and_document(conn, workspace_id=request.workspace_id, name=request.name, content=request.content, mime_type=request.mime_type)
        event = event_envelope(event_type="document.ingested", producer_type="human", producer_id=str(user_id), workspace_id=str(request.workspace_id), correlation_id=str(uuid.uuid4()), payload={"document_id": str(document_id), "source_id": str(source_id), "name": request.name})
        conn.execute("""insert into public.events (id,workspace_id,event_type,producer_type,producer_id,event_time,recorded_at,correlation_id,schema_version,payload)
            values (%(id)s,%(workspace_id)s,%(event_type)s,%(producer_type)s,%(producer_id)s,%(event_time)s,%(recorded_at)s,%(correlation_id)s,%(schema_version)s,%(payload)s::jsonb)""", {**event, "payload": json.dumps(event["payload"])})
        event_id = uuid.UUID(event["id"])
        claim_ids = persist_candidate_claims(conn, workspace_id=request.workspace_id, source_id=source_id, event_id=event_id, text=request.content)
        for claim, claim_id in zip(extract_candidate_claims(request.content), claim_ids):
            conn.execute("""insert into public.evidence (workspace_id,claim_id,source_id,event_id,relation,strength,extraction_method,excerpt)
                values (%s,%s,%s,%s,'supports',%s,'deterministic_candidate',%s)""", (request.workspace_id, claim_id, source_id, event_id, claim.confidence, claim.excerpt))
        conn.commit()
        count = conn.execute("select count(*) from public.document_chunks where document_id=%s", (document_id,)).fetchone()[0]
    return {"document_id": str(document_id), "source_id": str(source_id), "chunks": count, "candidate_claims": len(claim_ids), "claims_are_unverified": True}


@app.post("/v1/reindex/embeddings")
async def reindex_embeddings(request: ReindexRequest, user_id: uuid.UUID = Depends(current_user)) -> dict[str, int]:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    gateway = ReasoningGateway()
    try:
        with psycopg.connect(settings.database_url) as conn:
            require_workspace_access(conn, request.workspace_id, user_id)
            if request.document_id:
                rows = conn.execute("select id, content from public.document_chunks where workspace_id=%s and document_id=%s order by chunk_index", (request.workspace_id, request.document_id)).fetchall()
            else:
                rows = conn.execute("select id, content from public.document_chunks where workspace_id=%s order by created_at, chunk_index", (request.workspace_id,)).fetchall()
            updated = 0
            for start in range(0, len(rows), request.batch_size):
                batch = rows[start : start + request.batch_size]
                result = await gateway.embed([row[1] for row in batch])
                if any(len(vector) != 1536 for vector in result["embeddings"]):
                    raise ReasoningError("Configured embedding model must produce 1536 dimensions")
                for (chunk_id, _), vector in zip(batch, result["embeddings"]):
                    vector_text = "[" + ",".join(str(float(value)) for value in vector) + "]"
                    conn.execute("update public.document_chunks set embedding=%s::vector where id=%s and workspace_id=%s", (vector_text, chunk_id, request.workspace_id))
                    updated += 1
            conn.commit()
    except ReasoningError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"selected": len(rows), "embedded": updated}


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
                embedding = embedding_result["embeddings"][0]
                if len(embedding) == 1536:
                    semantic = retrieve_semantic(conn, workspace_id=request.workspace_id, embedding=embedding)
            except ReasoningError:
                semantic = []
        evidence = merge_retrieval_results(lexical, semantic)
        context = "\n\n".join(f"[Evidence {i + 1}] {item['document']} (chunk {item['chunk_index']}, score {item['score']:.3f})\n{item['content']}" for i, item in enumerate(evidence))
        conn.commit()
    try:
        result = await gateway.complete(question=request.question, context=context, model=request.model)
    except ReasoningError as exc:
        raise HTTPException(502, str(exc)) from exc
    run_id = uuid.uuid4()
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        conn.execute("""insert into public.reasoning_runs (id,workspace_id,session_id,question,mode,status,answer,started_at,completed_at,metadata)
            values (%s,%s,%s,%s,%s,'completed',%s,now(),now(),%s::jsonb)""", (run_id, request.workspace_id, session_id, request.question, request.mode, result["response"], json.dumps({"evidence_count": len(evidence), "lexical_count": len(lexical), "semantic_count": len(semantic)})))
        conn.execute("""insert into public.model_contributions (reasoning_run_id,model_id,provider,response,latency_ms,evidence_ids)
            values (%s,%s,%s,%s,%s,%s)""", (run_id, result["model"], result["provider"], result["response"], result["latency_ms"], [item["chunk_id"] for item in evidence]))
        _, assistant_event_id = record_message(conn, workspace_id=request.workspace_id, session_id=session_id, role="assistant", content=result["response"], source_id=None, correlation_id=correlation_id, causation_id=user_event_id)
        conn.execute("update public.events set aggregate_type='reasoning_run', aggregate_id=%s where id=%s", (run_id, assistant_event_id))
        if not evidence:
            gap = event_envelope(event_type="epistemic_gap.detected", producer_type="system", workspace_id=str(request.workspace_id), session_id=str(session_id), correlation_id=str(correlation_id), payload={"reasoning_run_id": str(run_id), "gap_type": "missing_evidence"})
            conn.execute("""insert into public.epistemic_gaps (workspace_id,reasoning_run_id,description,gap_type,severity,resolution_hint)
                values (%s,%s,%s,'missing_evidence',1.0,'Ingest or retrieve supporting source material before treating the answer as supported.')""", (request.workspace_id, run_id, "No indexed evidence matched the question."))
            conn.execute("""insert into public.events (id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,correlation_id,schema_version,payload)
                values (%(id)s,%(workspace_id)s,%(session_id)s,%(event_type)s,%(producer_type)s,%(event_time)s,%(recorded_at)s,%(correlation_id)s,%(schema_version)s,%(payload)s::jsonb)""", {**gap, "payload": json.dumps(gap["payload"])})
        conn.commit()
    return {"answer": result["response"], "session_id": str(session_id), "reasoning_run_id": str(run_id), "model": result["model"], "provider": result["provider"], "latency_ms": result["latency_ms"], "evidence": evidence, "trace": {"correlation_id": str(correlation_id), "user_event": str(user_event_id), "assistant_event": str(assistant_event_id), "retrieval_count": len(evidence), "retrieval_mode": "hybrid" if semantic else "lexical"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host=os.getenv("AURORA_HOST", "127.0.0.1"), port=int(os.getenv("AURORA_PORT", "8000")), reload=True)
