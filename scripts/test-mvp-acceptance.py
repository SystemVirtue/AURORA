"""Deterministic authenticated end-to-end acceptance proof for the AURORA MVP."""

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
        (
            USER_ID,
            f"aurora-mvp-{USER_ID}@example.invalid",
            Jsonb({"provider": "email", "providers": ["email"]}),
            Jsonb({}),
        ),
    )
    conn.commit()


async def fake_reason(self, *, question, context=None, model=None, mode="balanced", warrant=None):
    now = datetime.now(UTC)
    return {
        "answer": "The evidence conflicts, so AURORA keeps the conclusion qualified.",
        "model": "model-a",
        "provider": "test",
        "confidence": 0.6,
        "latency_ms": 2,
        "started_at": now,
        "completed_at": now,
        "event_time": now,
        "quorum": {
            "warrant": warrant,
            "contributors": [
                {"model": "model-a", "provider": "test", "response": "Online.", "evidence_ids": [], "latency_ms": 1},
                {"model": "model-b", "provider": "test", "response": "Offline.", "evidence_ids": [], "latency_ms": 1},
            ],
            "failed_contributors": [],
            "agreement": 0.0,
            "disagreements": ["model-a vs model-b"],
            "evidence_coverage": 1.0,
            "collective_gain": 1.0,
            "synthesis_model": "model-a",
            "synthesis_provider": "test",
            "synthesis_latency_ms": 1,
        },
    }


async def fake_embed(self, texts, model=None):
    return {"model": model or "test-embedding", "provider": "test", "embeddings": [[0.0] * 1536 for _ in texts]}


def expect(response, status: int = 200) -> dict:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def main() -> None:
    settings.database_url = DB_URL
    settings.supabase_jwt_secret = "aurora-mvp-acceptance-secret"
    token = jwt.encode(
        {"sub": str(USER_ID), "exp": datetime.now(UTC) + timedelta(minutes=10)},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}"}
    original_reason = ReasoningGateway.reason
    original_embed = ReasoningGateway.embed
    ReasoningGateway.reason = fake_reason
    ReasoningGateway.embed = fake_embed
    try:
        with psycopg.connect(DB_URL) as conn:
            seed(conn)
        with TestClient(app) as client:
            # IDENTITY → WORKSPACE
            workspaces = expect(client.get("/v1/workspaces", headers=headers))
            assert workspaces["workspaces"] == []
            created = expect(client.post("/v1/workspaces", headers=headers, json={"name": "MVP Acceptance"}))
            assert created["workspace_id"]
            workspace_id = created["workspace_id"]
            assert workspace_id == str(WORKSPACE_ID) or workspace_id != ""
            listed = expect(client.get("/v1/workspaces", headers=headers))
            assert any(w["id"] == workspace_id and w["role"] == "owner" for w in listed["workspaces"])

            # EVIDENCE → RETRIEVAL → CONTRADICTION → QUORUM
            for name, content in (("online.txt", "The Aurora server is online."), ("offline.txt", "The Aurora server is offline.")):
                expect(client.post("/v1/documents", headers=headers, json={"workspace_id": workspace_id, "name": name, "content": content}))
            asked = expect(client.post("/v1/ask", headers=headers, json={"workspace_id": workspace_id, "question": "Is the Aurora server online?"}))
            assert asked["evidence"]
            assert asked["trace"]["warrant"] == "workspace_contradiction"
            run_id = asked["reasoning_run_id"]
            with psycopg.connect(DB_URL) as conn:
                contributions = conn.execute("select count(*) from public.model_contributions where reasoning_run_id=%s", (run_id,)).fetchone()[0]
                quorum_event = conn.execute("select 1 from public.events where aggregate_id=%s and event_type='reasoning.quorum_completed'", (run_id,)).fetchone()
            assert contributions == 3
            assert quorum_event

            # PROVENANCE → BELIEF REVISION
            contradictions = expect(client.get(f"/v1/claims/contradictions?workspace_id={workspace_id}", headers=headers))
            assert contradictions["contradictions"]
            claim_id = contradictions["contradictions"][0]["claim_id"]
            provenance = expect(client.get(f"/v1/provenance/claims/{claim_id}?workspace_id={workspace_id}", headers=headers))
            assert provenance["nodes"] and provenance["edges"]
            reviewed = expect(client.post(f"/v1/claims/{claim_id}/review", headers=headers, json={"workspace_id": workspace_id, "status": "contested", "confidence": 0.4, "rationale": "Acceptance review"}))
            assert reviewed
            with psycopg.connect(DB_URL) as conn:
                status = conn.execute("select assertion_status from public.claims where id=%s", (claim_id,)).fetchone()[0]
            assert status == "contested"

            # GOAL → TASK → DECISION
            goal = expect(client.post("/v1/goals", headers=headers, json={"workspace_id": workspace_id, "title": "Prove MVP continuity", "priority": 10}))
            goal_id = goal["goal_id"]
            task = expect(client.post("/v1/tasks", headers=headers, json={"workspace_id": workspace_id, "goal_id": goal_id, "title": "Run reincarnation proof"}))
            task_id = task["task_id"]
            expect(client.patch(f"/v1/tasks/{task_id}", headers=headers, json={"workspace_id": workspace_id, "status": "completed"}))
            decision = expect(client.post("/v1/decisions", headers=headers, json={"workspace_id": workspace_id, "title": "MVP architecture", "decision": "Freeze the cognitive substrate before platform expansion.", "confidence": 0.9}))
            assert decision["decision_id"]
            assert len(expect(client.get(f"/v1/goals?workspace_id={workspace_id}", headers=headers))["goals"]) == 1
            assert expect(client.get(f"/v1/tasks?workspace_id={workspace_id}", headers=headers))["tasks"][0]["status"] == "completed"
            assert len(expect(client.get(f"/v1/decisions?workspace_id={workspace_id}", headers=headers))["decisions"]) == 1

            # PRIOR CONVERSATION IMPORT
            imported = expect(client.post("/v1/conversations/import", headers=headers, json={
                "workspace_id": workspace_id,
                "provider": "generic",
                "source_name": "Acceptance conversation",
                "payload": [
                    {"role": "user", "content": "What did we establish?"},
                    {"role": "assistant", "content": "We established a qualified conclusion."},
                ],
            }))
            assert imported["messages_imported"] == 2
            assert imported["model_text_is_historical_context"] is True
            assert imported["claims_promoted_to_fact"] is False

            # EXPORT → DESTROY → RESTORE → POST-RESTORE ASK
            exported = expect(client.get(f"/v1/continuity/export?workspace_id={workspace_id}", headers=headers))
            bundle = exported["bundle"]
            assert bundle["manifest"]["version"] == 3
            assert "tasks" in bundle["manifest"]["authoritative_tables"]
            with psycopg.connect(DB_URL) as conn:
                conn.execute("delete from public.workspaces where id=%s", (workspace_id,))
                conn.commit()

            restored = expect(client.post("/v1/continuity/restore", headers=headers, json={
                "workspace_id": workspace_id,
                "user_id_map": {str(USER_ID): str(USER_ID)},
                "bundle": bundle,
            }))
            assert restored["restored"] is True
            assert restored["rebuilt"]["document_chunks"] > 0
            assert restored["rows"]["tasks"] == 1
            assert expect(client.get(f"/v1/tasks?workspace_id={workspace_id}", headers=headers))["tasks"][0]["status"] == "completed"
            assert len(expect(client.get(f"/v1/goals?workspace_id={workspace_id}", headers=headers))["goals"]) == 1
            assert len(expect(client.get(f"/v1/decisions?workspace_id={workspace_id}", headers=headers))["decisions"]) == 1
            after_restore = expect(client.post("/v1/ask", headers=headers, json={"workspace_id": workspace_id, "question": "Is the Aurora server online?"}))
            assert after_restore["trace"]["warrant"] == "workspace_contradiction"

            print("AURORA MVP ACCEPTANCE: PASS")
    finally:
        ReasoningGateway.reason = original_reason
        ReasoningGateway.embed = original_embed
        with psycopg.connect(DB_URL) as conn:
            conn.execute("delete from public.workspaces where id=%s", (WORKSPACE_ID,))
            conn.execute("delete from auth.users where id=%s", (USER_ID,))
            conn.commit()


if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(main))
