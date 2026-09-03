from __future__ import annotations

import os
import uuid

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aurora.core import event_envelope, settings
from aurora.gateway import ReasoningError, ReasoningGateway

app = FastAPI(title="AURORA", version="0.1.0")


class AskRequest(BaseModel):
    workspace_id: uuid.UUID
    question: str = Field(min_length=1, max_length=10000)
    session_id: uuid.UUID | None = None
    model: str | None = None
    mode: str = "balanced"


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


@app.post("/v1/ask")
async def ask(request: AskRequest) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")

    gateway = ReasoningGateway()
    try:
        result = await gateway.complete(question=request.question, model=request.model)
    except ReasoningError as exc:
        raise HTTPException(502, str(exc)) from exc

    run_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """insert into public.reasoning_runs
                   (id, workspace_id, session_id, question, mode, status, answer, started_at, completed_at)
                   values (%s,%s,%s,%s,%s,'completed',%s,now(),now())""",
                (run_id, request.workspace_id, request.session_id, request.question, request.mode, result["response"]),
            )
            cur.execute(
                """insert into public.model_contributions
                   (reasoning_run_id, model_id, provider, response, latency_ms)
                   values (%s,%s,%s,%s,%s)""",
                (run_id, result["model"], result["provider"], result["response"], result["latency_ms"]),
            )
            event = event_envelope(
                event_type="reasoning.completed",
                producer_type="model",
                workspace_id=str(request.workspace_id),
                session_id=str(request.session_id) if request.session_id else None,
                correlation_id=str(correlation_id),
                payload={"reasoning_run_id": str(run_id), "question": request.question, "model": result["model"]},
            )
            cur.execute(
                """insert into public.events
                   (id, workspace_id, session_id, event_type, producer_type, event_time, recorded_at,
                    correlation_id, schema_version, payload)
                   values (%(id)s,%(workspace_id)s,%(session_id)s,%(event_type)s,%(producer_type)s,
                           %(event_time)s,%(recorded_at)s,%(correlation_id)s,%(schema_version)s,%(payload)s::jsonb)""",
                {**event, "payload": __import__("json").dumps(event["payload"])},
            )
        conn.commit()

    return {
        "answer": result["response"],
        "reasoning_run_id": str(run_id),
        "model": result["model"],
        "provider": result["provider"],
        "latency_ms": result["latency_ms"],
        "trace": {"event_type": "reasoning.completed", "correlation_id": str(correlation_id)},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host=os.getenv("AURORA_HOST", "127.0.0.1"), port=int(os.getenv("AURORA_PORT", "8000")), reload=True)
