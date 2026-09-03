"""Live API integration proof for QUORUM, authenticated continuity, and reincarnation."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import psycopg
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from apps.api.main import app
from aurora.core import settings
from aurora.gateway import ReasoningGateway

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
USER_ID = uuid.uuid4()
WORKSPACE_ID = uuid.uuid4()


def seed(conn: psycopg.Connection) -> None:
    conn.execute(
        """insert into auth.users
           (id, aud, role, email, encrypted_password, raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
           values (%s, 'authenticated', 'authenticated', %s, '', %s, %s, now(), now())""",
        (USER_ID, f"aurora-api-{USER_ID}@example.invalid", Jsonb({"provider": "email", "providers": ["email"]}), Jsonb({})),
    )
    conn.execute(
        "insert into public.workspaces (id,name,slug,created_by) values (%s,%s,%s,%s)",
        (WORKSPACE_ID, "API QUORUM Integration", f"api-quorum-{USER_ID}", USER_ID),
    )
    conn.execute(
        "insert into public.workspace_members (workspace_id,user_id,role) values (%s,%s,'owner')",
        (WORKSPACE_ID, USER_ID),
    )
    conn.commit()


async def fake_reason(self, *, question, context=None, model=None, mode="balanced", warrant=None):
    now = datetime.now(UTC)
    return {
        "answer": "The evidence conflicts; the answer should remain qualified.",
        "model": "model-a", "provider": "test", "confidence": 0.6, "latency_ms": 2,
        "started_at": now, "completed_at": now, "event_time": now,
        "quorum": {
            "warrant": warrant,
            "contributors": [
                {"model": "model-a", "provider": "test", "response": "Online.", "evidence_ids": [], "latency_ms": 1},
                {"model": "model-b", "provider": "test", "response": "Offline.", "evidence_ids": [], "latency_ms": 1},
            ],
            "failed_contributors": [], "agreement": 0.0, "disagreements": ["model-a vs model-b"],
            "evidence_coverage": 1.0, "collective_gain": 1.0,
            "synthesis_model": "model-a", "synthesis_provider": "test", "synthesis_latency_ms": 1,
        },
    }


async def fake_embed(self, texts, model=None):
    return {"model": model or "test-embedding", "provider": "test", "embeddings": [[0.0] * 1536 for _ in texts]}


def main() -> None:
    settings.database_url = DB_URL
    settings.supabase_jwt_secret = "aurora-api-integration-secret"
    token = jwt.encode(
        {"sub": str(USER_ID), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.supabase_jwt_secret, algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}"}
    with psycopg.connect(DB_URL) as conn:
        seed(conn)
    original_reason = ReasoningGateway.reason
    original_embed = ReasoningGateway.embed
    ReasoningGateway.reason = fake_reason
    ReasoningGateway.embed = fake_embed
    try:
        with TestClient(app) as client:
            for content in ("The Aurora server is online.", "The Aurora server is offline."):
                response = client.post(
                    "/v1/documents", headers=headers,
                    json={"workspace_id": str(WORKSPACE_ID), "name": "state.txt", "content": content},
                )
                assert response.status_code == 200, response.text
            response = client.post(
                "/v1/ask", headers=headers,
                json={"workspace_id": str(WORKSPACE_ID), "question": "Is the Aurora server online?"},
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["trace"]["warrant"] == "workspace_contradiction"
            run_id = body["reasoning_run_id"]
            with psycopg.connect(DB_URL) as conn:
                count = conn.execute(
                    "select count(*) from public.model_contributions where reasoning_run_id=%s", (run_id,)
                ).fetchone()[0]
                event = conn.execute(
                    "select 1 from public.events where aggregate_id=%s and event_type='reasoning.quorum_completed'",
                    (run_id,),
                ).fetchone()
            assert count == 3
            assert event

            exported = client.get(f"/v1/continuity/export?workspace_id={WORKSPACE_ID}", headers=headers)
            assert exported.status_code == 200, exported.text
            bundle = exported.json()["bundle"]
            with psycopg.connect(DB_URL) as conn:
                conn.execute("delete from public.workspaces where id=%s", (WORKSPACE_ID,))
                conn.commit()

            restored = client.post(
                "/v1/continuity/restore", headers=headers,
                json={"workspace_id": str(WORKSPACE_ID), "user_id_map": {str(USER_ID): str(USER_ID)}, "bundle": bundle},
            )
            assert restored.status_code == 200, restored.text
            assert restored.json()["rebuilt"]["document_chunks"] > 0

            reindexed = client.post(
                "/v1/reindex/embeddings", headers=headers,
                json={"workspace_id": str(WORKSPACE_ID)},
            )
            assert reindexed.status_code == 200, reindexed.text
            assert reindexed.json()["embedded"] > 0

            after_restore = client.post(
                "/v1/ask", headers=headers,
                json={"workspace_id": str(WORKSPACE_ID), "question": "Is the Aurora server online?"},
            )
            assert after_restore.status_code == 200, after_restore.text
            assert after_restore.json()["trace"]["warrant"] == "workspace_contradiction"
            print("API QUORUM + authenticated continuity + reindex/ask: PASS")
    finally:
        ReasoningGateway.reason = original_reason
        ReasoningGateway.embed = original_embed
        with psycopg.connect(DB_URL) as conn:
            conn.execute("delete from public.workspaces where id=%s", (WORKSPACE_ID,))
            conn.execute("delete from auth.users where id=%s", (USER_ID,))
            conn.commit()


if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(main))
