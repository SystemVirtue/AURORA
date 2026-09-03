from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aurora.core import settings

router = APIRouter(prefix="/v1/provenance", tags=["provenance"])
bearer = HTTPBearer(auto_error=False)


def authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
) -> uuid.UUID:
    """Delegate JWT validation to the canonical API dependency without import-time cycles."""
    from apps.api.main import current_user
    return current_user(credentials)


@router.get("/claims/{claim_id}")
def claim_provenance(
    claim_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID = Depends(authenticated_user),  # noqa: B008
) -> dict:
    """Return an inspectable claim -> evidence -> source/event -> reasoning graph."""
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        if not conn.execute(
            "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
            (workspace_id, user_id),
        ).fetchone():
            raise HTTPException(403, "User is not a member of this workspace")

        claim = conn.execute(
            """select id, subject, predicate, object, assertion_status, confidence, source_id, event_id
               from public.claims where id=%s and workspace_id=%s""",
            (claim_id, workspace_id),
        ).fetchone()
        if not claim:
            raise HTTPException(404, "Claim not found")

        evidence = conn.execute(
            """select id, relation, strength, extraction_method, excerpt, source_id, event_id
               from public.evidence where claim_id=%s and workspace_id=%s order by id""",
            (claim_id, workspace_id),
        ).fetchall()
        source_ids = {claim[6]} if claim[6] else set()
        event_ids = {claim[7]} if claim[7] else set()
        source_ids.update(row[5] for row in evidence if row[5])
        event_ids.update(row[6] for row in evidence if row[6])

        sources = []
        if source_ids:
            sources = conn.execute(
                "select id, source_type, name, provider, external_id from public.sources where workspace_id=%s and id = any(%s::uuid[]) order by id",
                (workspace_id, list(source_ids)),
            ).fetchall()

        evidence_ids = [row[0] for row in evidence]
        contributions = []
        if evidence_ids:
            contributions = conn.execute(
                """select mc.id, mc.reasoning_run_id, mc.model_id, mc.provider, mc.role, mc.confidence,
                          mc.latency_ms, mc.estimated_cost, mc.evidence_ids, mc.response
                     from public.model_contributions mc
                     join public.reasoning_runs rr on rr.id=mc.reasoning_run_id
                    where rr.workspace_id=%s and mc.evidence_ids && %s::uuid[]
                    order by mc.created_at, mc.id""",
                (workspace_id, evidence_ids),
            ).fetchall()

        run_ids = list(dict.fromkeys(row[1] for row in contributions))
        runs = []
        if run_ids:
            runs = conn.execute(
                """select id, session_id, question, mode, status, answer, confidence, started_at, completed_at
                   from public.reasoning_runs where workspace_id=%s and id = any(%s::uuid[]) order by started_at, id""",
                (workspace_id, run_ids),
            ).fetchall()

        reasoning_events = []
        if run_ids:
            reasoning_events = conn.execute(
                """select id, session_id, event_type, producer_type, producer_id, event_time,
                          recorded_at, correlation_id, aggregate_type, aggregate_id, payload
                   from public.events where workspace_id=%s and aggregate_type='reasoning_run'
                     and aggregate_id = any(%s::uuid[]) order by recorded_at, id""",
                (workspace_id, run_ids),
            ).fetchall()

        events = []
        if event_ids:
            events = conn.execute(
                """select id, session_id, event_type, producer_type, producer_id, event_time,
                          recorded_at, correlation_id, aggregate_type, aggregate_id, payload
                   from public.events where workspace_id=%s and id = any(%s::uuid[]) order by recorded_at, id""",
                (workspace_id, list(event_ids)),
            ).fetchall()

    nodes = [
        {"id": f"claim:{claim[0]}", "type": "claim", "label": f"{claim[1]} {claim[2]} {claim[3]}",
         "status": claim[4], "confidence": float(claim[5]) if claim[5] is not None else None}
    ]
    edges = []
    evidence_id_set = {item[0] for item in evidence}
    for row in evidence:
        nodes.append({"id": f"evidence:{row[0]}", "type": "evidence", "label": row[4] or row[1],
                      "relation": row[1], "strength": float(row[2]) if row[2] is not None else None,
                      "extraction_method": row[3]})
        edges.append({"source": f"claim:{claim[0]}", "target": f"evidence:{row[0]}", "relation": row[1]})
    for row in sources:
        nodes.append({"id": f"source:{row[0]}", "type": "source", "label": row[2] or str(row[0]),
                      "source_type": row[1], "provider": row[3], "external_id": row[4]})
    for row in evidence:
        if row[5]:
            edges.append({"source": f"evidence:{row[0]}", "target": f"source:{row[5]}", "relation": "derived_from"})
    for row in events:
        nodes.append({"id": f"event:{row[0]}", "type": "event", "label": row[2], "producer_type": row[3],
                      "producer_id": str(row[4]) if row[4] else None, "event_time": row[5].isoformat(),
                      "recorded_at": row[6].isoformat(), "correlation_id": str(row[7]) if row[7] else None,
                      "payload": row[10]})
    for row in evidence:
        if row[6]:
            edges.append({"source": f"evidence:{row[0]}", "target": f"event:{row[6]}", "relation": "captured_by"})
    for row in runs:
        nodes.append({"id": f"reasoning_run:{row[0]}", "type": "reasoning_run", "label": row[2],
                      "mode": row[3], "status": row[4], "confidence": float(row[6]) if row[6] is not None else None,
                      "started_at": row[7].isoformat(), "completed_at": row[8].isoformat() if row[8] else None})
        for event in reasoning_events:
            if event[9] == row[0]:
                edges.append({"source": f"reasoning_run:{row[0]}", "target": f"event:{event[0]}", "relation": "recorded_as"})
    synthesis_by_run = {}
    for row in contributions:
        nodes.append({"id": f"contribution:{row[0]}", "type": "model_contribution", "label": row[2],
                      "provider": row[3], "role": row[4], "confidence": float(row[5]) if row[5] is not None else None,
                      "latency_ms": row[6], "estimated_cost": float(row[7]) if row[7] is not None else None,
                      "response": row[9]})
        edges.append({"source": f"reasoning_run:{row[1]}", "target": f"contribution:{row[0]}", "relation": "contributed"})
        if row[4] == "synthesizer":
            synthesis_by_run[row[1]] = row[0]
        for evidence_id in row[8] or []:
            if evidence_id in evidence_id_set:
                edges.append({"source": f"contribution:{row[0]}", "target": f"evidence:{evidence_id}", "relation": "used"})
    for row in contributions:
        synthesis_id = synthesis_by_run.get(row[1])
        if synthesis_id and row[4] == "quorum_contributor":
            edges.append({"source": f"contribution:{row[0]}", "target": f"contribution:{synthesis_id}", "relation": "synthesized_into"})
    for event in reasoning_events:
        nodes.append({"id": f"event:{event[0]}", "type": "event", "label": event[2], "producer_type": event[3],
                      "producer_id": str(event[4]) if event[4] else None, "event_time": event[5].isoformat(),
                      "recorded_at": event[6].isoformat(), "correlation_id": str(event[7]) if event[7] else None,
                      "payload": event[10]})

    return {"workspace_id": str(workspace_id), "claim_id": str(claim_id), "nodes": nodes, "edges": edges}
