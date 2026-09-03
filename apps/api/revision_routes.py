from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.core import settings

router = APIRouter(prefix="/v1/claims", tags=["claims"])
bearer = HTTPBearer(auto_error=False)


class ClaimReviewRequest(BaseModel):
    workspace_id: uuid.UUID
    status: str = Field(pattern="^(unverified|supported|contested|rejected|superseded)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = Field(default=None, max_length=5000)


@router.post("/{claim_id}/review")
def review_claim(
    claim_id: uuid.UUID,
    request: ClaimReviewRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """Thin adapter; the database function owns revision and temporal semantics."""
    from apps.api.main import current_user

    user_id = current_user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        member = conn.execute(
            "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
            (request.workspace_id, user_id),
        ).fetchone()
        if not member:
            raise HTTPException(403, "User is not a member of this workspace")
        claim = conn.execute(
            "select 1 from public.claims where id=%s and workspace_id=%s",
            (claim_id, request.workspace_id),
        ).fetchone()
        if not claim:
            raise HTTPException(404, "Claim not found")
        try:
            belief_id = conn.execute(
                "select public.revise_claim(%s,%s,%s,%s,%s)",
                (claim_id, request.status, user_id, request.confidence, request.rationale),
            ).fetchone()[0]
            conn.commit()
        except psycopg.Error as exc:
            conn.rollback()
            raise HTTPException(409, "Claim revision could not be applied") from exc
    return {
        "claim_id": str(claim_id),
        "status": request.status,
        "belief_id": str(belief_id) if belief_id else None,
        "reviewed_by": str(user_id),
    }
