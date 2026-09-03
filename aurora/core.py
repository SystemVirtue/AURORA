from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Settings:
    database_url: str | None = os.getenv("DATABASE_URL")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    default_model: str | None = os.getenv("AURORA_DEFAULT_MODEL")
    embedding_model: str = os.getenv("AURORA_EMBEDDING_MODEL", "text-embedding-3-small")
    reasoning_mode: str = os.getenv("AURORA_REASONING_MODE", "balanced")
    supabase_jwt_secret: str | None = os.getenv("SUPABASE_JWT_SECRET")


settings = Settings()


def new_id() -> uuid.UUID:
    return uuid.uuid4()


def event_envelope(
    *,
    event_type: str,
    producer_type: str,
    payload: dict[str, Any],
    workspace_id: str,
    session_id: str | None = None,
    causation_id: str | None = None,
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
    producer_id: str | None = None,
) -> dict[str, Any]:
    now = utcnow().isoformat()
    return {
        "id": str(new_id()),
        "workspace_id": workspace_id,
        "session_id": session_id,
        "event_type": event_type,
        "producer_type": producer_type,
        "producer_id": producer_id,
        "event_time": now,
        "recorded_at": now,
        "causation_id": causation_id,
        "correlation_id": correlation_id,
        "schema_version": 1,
        "idempotency_key": idempotency_key,
        "payload": payload,
    }
