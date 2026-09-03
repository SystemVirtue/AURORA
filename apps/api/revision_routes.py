from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aurora.core import settings

router = APIRouter(prefix="/v1/claims", tags=["claims"])


class ClaimReviewRequest(BaseModel):
    workspace_id: uuid.UUID
    status: str = Field(pattern="^(unverified|supported|contested|rejected|superseded)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = Field(default=None, max_length=5000)


@router.post("/{claim_id}/review")
def review_claim(
    claim_id: uuid.UUID,
    request: ClaimReviewRequest,
    user_id: uuid.UUID,
) -> dict:
    """Thin persistence adapter; the database function owns revision semantics."""
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        member = conn.execute(
            "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
            (request.workspace_id, user_id),
        ).fetchone()
        if not member:
            raise HTTPException(403, "User is not a member of this workspace")
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


def current_user_dependency():
    """Imported lazily to avoid a module cycle with the API application."""
    from apps.api.main import current_user
    return Depends(current_user)
