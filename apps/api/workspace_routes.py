# ruff: noqa: B008, I001
from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.core import settings

router = APIRouter(prefix="/v1", tags=["workspaces"])
bearer = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None) -> uuid.UUID:
    from apps.api.main import current_user
    return current_user(credentials)


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=100)


@router.get("/workspaces")
def list_workspaces(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    with psycopg.connect(settings.database_url) as conn:
        rows = conn.execute(
            """select w.id,w.name,w.slug,wm.role
               from public.workspaces w
               join public.workspace_members wm on wm.workspace_id=w.id
               where wm.user_id=%s order by w.created_at""",
            (user_id,),
        ).fetchall()
    return {"workspaces": [{"id": str(r[0]), "name": r[1], "slug": r[2], "role": r[3]} for r in rows]}


@router.post("/workspaces")
def create_workspace(
    request: WorkspaceCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    user_id = _user(credentials)
    slug = request.slug or "-".join(request.name.lower().split())
    slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")[:100].strip("-")
    if not slug:
        raise HTTPException(422, "A non-empty workspace slug is required")
    workspace_id = uuid.uuid4()
    with psycopg.connect(settings.database_url) as conn:
        try:
            conn.execute(
                "insert into public.workspaces(id,name,slug,created_by) values (%s,%s,%s,%s)",
                (workspace_id, request.name, slug, user_id),
            )
            conn.execute(
                "insert into public.workspace_members(workspace_id,user_id,role) values (%s,%s,'owner')",
                (workspace_id, user_id),
            )
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            conn.rollback()
            raise HTTPException(409, "Workspace slug already exists") from exc
    return {"workspace_id": str(workspace_id), "name": request.name, "slug": slug, "role": "owner"}
