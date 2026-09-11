# ruff: noqa: B008
from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from apps.api.action_routes import router as action_router
from apps.api.knowledge_routes import router as knowledge_router
from apps.api.model_routes import router as model_router
from apps.api.puter_routes import router as puter_router
from aurora.core import settings

router = APIRouter(prefix="/v1", tags=["cognition"])
bearer = HTTPBearer(auto_error=False)


class ClaimReviewRequest(BaseModel):
    workspace_id: uuid.UUID
    status: str = Field(pattern="^(unverified|supported|contested|rejected|superseded)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str = Field(default="", max_length=10000)


def _user(credentials: HTTPAuthorizationCredentials | None) -> uuid.UUID:
    from apps.api.main import current_user

    return current_user(credentials)


@router.post("/claims/{claim_id}/review")
def review_claim(
    claim_id: uuid.UUID,
    request: ClaimReviewRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, str | None]:
    """Apply explicit human review to a claim and record the revision event."""
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    try:
        with psycopg.connect(settings.database_url) as conn:
            member = conn.execute(
                "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
                (request.workspace_id, user_id),
            ).fetchone()
            if not member:
                raise HTTPException(403, "User is not a member of this workspace")
            claim = conn.execute(
                "select id, status, confidence from public.claims where id=%s and workspace_id=%s",
                (claim_id, request.workspace_id),
            ).fetchone()
            if not claim:
                raise HTTPException(404, "Claim not found")
            conn.execute(
                "update public.claims set status=%s, confidence=coalesce(%s,confidence), updated_at=now() where id=%s and workspace_id=%s",
                (request.status, request.confidence, claim_id, request.workspace_id),
            )
            event_id = uuid.uuid4()
            conn.execute(
                "insert into public.events (id,workspace_id,event_type,producer_type,producer_id,event_time,recorded_at,aggregate_type,aggregate_id,schema_version,payload) values (%s,%s,'claim.reviewed','human',%s,now(),now(),'claim',%s,1,%s::jsonb)",
                (event_id, request.workspace_id, user_id, claim_id, __import__('json').dumps({"from_status": claim[1], "to_status": request.status, "confidence": request.confidence, "rationale": request.rationale})),
            )
            conn.commit()
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(500, "Unable to review claim") from exc
    return {"claim_id": str(claim_id), "status": request.status, "confidence": str(request.confidence) if request.confidence is not None else None}


router.include_router(action_router)
router.include_router(knowledge_router)
router.include_router(model_router)
router.include_router(puter_router)