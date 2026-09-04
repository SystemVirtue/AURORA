# ruff: noqa: E701,E702
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import jwt
import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from apps.api.continuity_routes import router as continuity_router
from apps.api.provenance_routes import router as provenance_router
from apps.api.revision_routes import router as revision_router
from aurora.claims import extract_candidate_claims, persist_candidate_claims
from aurora.cognition import create_source_and_document, merge_retrieval_results, record_message, retrieve_lexical, retrieve_semantic
from aurora.core import event_envelope, settings
from aurora.gateway import ReasoningError, ReasoningGateway

app = FastAPI(title="AURORA", version="0.6.0")
bearer = HTTPBearer(auto_error=False)

if settings.allowed_cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "Accept"], max_age=600)

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
    if credentials is None or credentials.scheme.lower() != "bearer": raise HTTPException(401, "Bearer authentication required")
    if not settings.supabase_jwt_secret: raise HTTPException(503, "SUPABASE_JWT_SECRET is not configured")
    try:
        payload = jwt.decode(credentials.credentials, settings.supabase_jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]}, leeway=10)
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc: raise HTTPException(401, "Invalid authentication token") from exc

def require_workspace_access(conn, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not conn.execute("select 1 from public.workspace_members where workspace_id=%s and user_id=%s", (workspace_id, user_id)).fetchone(): raise HTTPException(403, "User is not a member of this workspace")

def require_session_access(conn, session_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not conn.execute("select 1 from public.sessions s join public.workspace_members wm on wm.workspace_id=s.workspace_id where s.id=%s and s.workspace_id=%s and wm.user_id=%s", (session_id, workspace_id, user_id)).fetchone(): raise HTTPException(404, "Session not found")

def _question_terms(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in {"the", "and", "that", "this", "with", "from"}}

def _relevant_contradiction_count(conn, workspace_id: uuid.UUID, question: str) -> int:
    rows = conn.execute("select subject, predicate, object, opposing_object from public.claim_contradictions(%s)", (workspace_id,)).fetchall()
    terms = _question_terms(question)
    return sum(1 for row in rows if terms & _question_terms(" ".join(str(value or "") for value in row))) if terms else 0

app.include_router(revision_router)
app.include_router(provenance_router)
app.include_router(continuity_router)

@app.get("/", include_in_schema=False)
def workspace_ui() -> FileResponse: return FileResponse(Path(__file__).resolve().parents[1] / "web" / "index.html")

@app.get("/health")
def health() -> dict[str, str]: return {"status": "ok", "service": "aurora-api"}

@app.get("/health/db")
def health_db() -> dict[str, str]:
    if not settings.database_url: raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn: conn.execute("select 1")
    return {"status": "ok", "database": "reachable"}

@app.get("/v1/claims/contradictions")
def claim_contradictions(workspace_id: uuid.UUID, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url: raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, workspace_id, user_id)
        rows = conn.execute("select claim_id, opposing_claim_id, subject, predicate, object, opposing_object from public.claim_contradictions(%s)", (workspace_id,)).fetchall()
    return {"workspace_id": str(workspace_id), "count": len(rows), "contradictions": [{"claim_id": str(r[0]), "opposing_claim_id": str(r[1]), "subject": r[2], "predicate": r[3], "object": r[4], "opposing_object": r[5]} for r in rows]}

@app.post("/v1/sessions")
def create_session(request: SessionRequest, user_id: uuid.UUID = Depends(current_user)) -> dict[str, str]:
    if not settings.database_url: raise HTTPException(503, "DATABASE_URL is not configured")
    session_id = uuid.uuid4()
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id); conn.execute("insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,%s)", (session_id, request.workspace_id, user_id, request.title)); conn.commit()
    return {"session_id": str(session_id)}

@app.post("/v1/documents")
def ingest_document(request: DocumentRequest, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url: raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        source_id, document_id = create_source_and_document(conn, workspace_id=request.workspace_id, name=request.name, content=request.content, mime_type=request.mime_type)
        event = event_envelope(event_type="document.ingested", producer_type="human", producer_id=str(user_id), workspace_id=str(request.workspace_id), correlation_id=str(uuid.uuid4()), payload={"document_id": str(document_id), "source_id": str(source_id), "name": request.name})
        conn.execute("insert into public.events (id,workspace_id,event_type,producer_type,producer_id,event_time,recorded_at,correlation_id,schema_version,payload) values (%(id)s,%(workspace_id)s,%(event_type)s,%(producer_type)s,%(producer_id)s,%(event_time)s,%(recorded_at)s,%(correlation_id)s,%(schema_version)s,%(payload)s::jsonb)", {**event, "payload": json.dumps(event["payload"])})
        event_id = uuid.UUID(event["id"]); candidates = extract_candidate_claims(request.content); claim_ids = persist_candidate_claims(conn, workspace_id=request.workspace_id, source_id=source_id, event_id=event_id, text=request.content)
        for claim, claim_id in zip(candidates, claim_ids): conn.execute("insert into public.evidence (workspace_id,claim_id,source_id,event_id,relation,strength,extraction_method,excerpt) values (%s,%s,%s,%s,'supports',%s,'deterministic_candidate',%s)", (request.workspace_id, claim_id, source_id, event_id, claim.confidence, claim.excerpt))
        conn.commit(); count = conn.execute("select count(*) from public.document_chunks where document_id=%s", (document_id,)).fetchone()[0]
    return {"document_id": str(document_id), "source_id": str(source_id), "chunks": count, "candidate_claims": len(claim_ids), "claims_are_unverified": True}

@app.post("/v1/reindex/embeddings")
async def reindex_embeddings(request: ReindexRequest, user_id: uuid.UUID = Depends(current_user)) -> dict[str, int]:
    if not settings.database_url: raise HTTPException(503, "DATABASE_URL is not configured")
    gateway = ReasoningGateway()
    try:
        with psycopg.connect(settings.database_url) as conn:
            require_workspace_access(conn, request.workspace_id, user_id); rows = conn.execute("select id, content from public.document_chunks where workspace_id=%s and document_id=%s order by chunk_index", (request.workspace_id, request.document_id)).fetchall() if request.document_id else conn.execute("select id, content from public.document_chunks where workspace_id=%s order by created_at, chunk_index", (request.workspace_id,)).fetchall(); updated = 0
            for start in range(0, len(rows), request.batch_size):
                batch = rows[start:start + request.batch_size]; result = await gateway.embed([row[1] for row in batch])
                if any(len(vector) != 1536 for vector in result["embeddings"]): raise ReasoningError("Configured embedding model must produce 1536 dimensions")
                for (chunk_id, _), vector in zip(batch, result["embeddings"]):
                    vector_text = "[" + ",".join(str(float(value)) for value in vector) + "]"; conn.execute("update public.document_chunks set embedding=%s::vector where id=%s and workspace_id=%s", (vector_text, chunk_id, request.workspace_id)); updated += 1
            conn.commit()
    except ReasoningError as exc: raise HTTPException(502, str(exc)) from exc
    return {"selected": len(rows), "embedded": updated}

@app.post("/v1/ask")
async def ask(request: AskRequest, user_id: uuid.UUID = Depends(current_user)) -> dict:
    if not settings.database_url: raise HTTPException(503, "DATABASE_URL is not configured")
    session_id = request.session_id or uuid.uuid4(); correlation_id = uuid.uuid4(); gateway = ReasoningGateway()
    with psycopg.connect(settings.database_url) as conn:
        require_workspace_access(conn, request.workspace_id, user_id)
        if request.session_id: require_session_access(conn, session_id, request.workspace_id, user_id)
        else: conn.execute("insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,%s)", (session_id, request.workspace_id, user_id, request.question[:100]))
        _, user_event_id = record_message(conn, workspace_id=request.workspace_id, session_id=session_id, role="user", content=request.question, source_id=None, correlation_id=correlation_id)
        lexical = retrieve_lexical(conn, workspace_id=request.workspace_id, question=request.question); semantic: list[dict] = []
        if settings.openai_api_key or settings.openrouter_api_key:
            try: embedding_result = await gateway.embed([request.question]); semantic = retrieve_semantic(conn, workspace_id=request.workspace_id, embedding=embedding_result["embeddings"][0], limit=8)
            except ReasoningError: semantic = []
        retrieved = merge_retrieval_results(lexical, semantic, limit=8); context = [{"content": item["content"], "evidence_id": item.get("evidence_id")} for item in retrieved]
        contradiction_count = _relevant_contradiction_count(conn, request.workspace_id, request.question); warrant = "workspace_contradiction" if contradiction_count else ("missing_evidence" if not context else None)
        try: result = await gateway.reason(question=request.question, context=context, model=request.model, mode=request.mode, warrant=warrant)
        except ReasoningError as exc: raise HTTPException(502, str(exc)) from exc
        reasoning_run_id = uuid.uuid4(); quorum = result.get("quorum"); metadata = {"correlation_id": str(correlation_id), "retrieval": retrieved, "contradiction_count": contradiction_count, "warrant": quorum.get("warrant") if quorum else warrant}
        if quorum: metadata["quorum"] = quorum
        conn.execute("insert into public.reasoning_runs (id,workspace_id,session_id,question,mode,status,answer,confidence,started_at,completed_at,metadata) values (%s,%s,%s,%s,%s,'completed',%s,%s,%s,%s,%s::jsonb)", (reasoning_run_id, request.workspace_id, session_id, request.question, "quorum" if quorum else request.mode, result["answer"], result.get("confidence"), result["started_at"], result["completed_at"], json.dumps(metadata)))
        evidence_ids = [item["evidence_id"] for item in retrieved if item.get("evidence_id")]
        if quorum:
            for contributor in quorum["contributors"]: conn.execute("insert into public.model_contributions (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids) values (%s,%s,%s,'quorum_contributor',%s,%s,%s,%s,%s)", (reasoning_run_id, contributor["model"], contributor.get("provider"), contributor["response"], None, contributor.get("latency_ms"), None, contributor.get("evidence_ids", evidence_ids)))
            conn.execute("insert into public.model_contributions (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids) values (%s,%s,%s,'synthesizer',%s,%s,%s,%s,%s)", (reasoning_run_id, quorum["synthesis_model"], quorum.get("synthesis_provider"), result["answer"], result.get("confidence"), quorum.get("synthesis_latency_ms"), None, evidence_ids))
        else: conn.execute("insert into public.model_contributions (reasoning_run_id,model_id,provider,role,response,confidence,latency_ms,estimated_cost,evidence_ids) values (%s,%s,%s,'reasoner',%s,%s,%s,%s,%s)", (reasoning_run_id, result["model"], result.get("provider"), result["answer"], result.get("confidence"), result.get("latency_ms"), result.get("estimated_cost"), evidence_ids))
        _, assistant_event_id = record_message(conn, workspace_id=request.workspace_id, session_id=session_id, role="assistant", content=result["answer"], source_id=None, correlation_id=correlation_id)
        if not retrieved: conn.execute("insert into public.epistemic_gaps (workspace_id,reasoning_run_id,description,gap_type,severity,status) values (%s,%s,%s,'missing_evidence',0.8,'open')", (request.workspace_id, reasoning_run_id, "No matching workspace evidence was retrieved."))
        reasoning_event_id = uuid.uuid4(); conn.execute("insert into public.events (id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,correlation_id,aggregate_type,aggregate_id,schema_version,payload) values (%s,%s,%s,'reasoning.completed','model',%s,%s,%s,'reasoning_run',%s,1,%s::jsonb)", (reasoning_event_id, request.workspace_id, session_id, result["event_time"], result["event_time"], correlation_id, reasoning_run_id, json.dumps({"evidence_ids": evidence_ids, "assistant_event_id": str(assistant_event_id)})))
        quorum_event_id = None
        if quorum:
            quorum_event_id = uuid.uuid4(); conn.execute("insert into public.events (id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,correlation_id,aggregate_type,aggregate_id,schema_version,payload) values (%s,%s,%s,'reasoning.quorum_completed','system',%s,%s,%s,'reasoning_run',%s,1,%s::jsonb)", (quorum_event_id, request.workspace_id, session_id, result["event_time"], result["event_time"], correlation_id, reasoning_run_id, json.dumps({"quorum": quorum})))
        conn.commit()
    response = {"session_id": str(session_id), "reasoning_run_id": str(reasoning_run_id), "answer": result["answer"], "evidence": retrieved, "evidence_ids": evidence_ids, "model": result["model"], "provider": result.get("provider"), "latency_ms": result.get("latency_ms"), "trace": {"correlation_id": str(correlation_id), "user_event_id": str(user_event_id), "assistant_event_id": str(assistant_event_id), "warrant": quorum.get("warrant") if quorum else warrant}}
    if quorum: response["quorum"] = quorum; response["trace"]["quorum_event_id"] = str(quorum_event_id)
    return response
