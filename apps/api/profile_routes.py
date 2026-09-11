# ruff: noqa: B008
from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.core import settings

router = APIRouter(prefix="/v1/profile", tags=["profile"])
bearer = HTTPBearer(auto_error=False)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=300)
    preferences: dict = Field(default_factory=dict)


class CredentialUpdate(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    secret: str | None = Field(default=None, max_length=20000)
    metadata: dict = Field(default_factory=dict)


def _user(credentials: HTTPAuthorizationCredentials | None) -> uuid.UUID:
    from apps.api.main import current_user
    return current_user(credentials)


def _ensure_profile(conn, user_id: uuid.UUID) -> None:
    conn.execute("insert into public.user_profiles (user_id) values (%s) on conflict (user_id) do nothing", (user_id,))


@router.get("")
def get_profile(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        _ensure_profile(conn, user_id)
        row = conn.execute("select display_name, timezone, default_model, preferences from public.user_profiles where user_id=%s", (user_id,)).fetchone()
        creds = conn.execute("select provider, label, metadata, secret_id is not null from public.user_credentials where user_id=%s order by provider, label", (user_id,)).fetchall()
        conn.commit()
    credentials_out = [{"provider": r[0], "label": r[1], "metadata": r[2], "configured": bool(r[3])} for r in creds]
    server_openrouter = bool(settings.openrouter_api_key)
    return {"user_id": str(user_id), "profile": {"display_name": row[0], "timezone": row[1], "default_model": row[2], "preferences": row[3] or {}}, "credentials": credentials_out, "openrouter": {"configured": server_openrouter, "source": "server_env" if server_openrouter else "user_profile"}}


@router.patch("")
def update_profile(request: ProfileUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        _ensure_profile(conn, user_id)
        conn.execute("update public.user_profiles set display_name=%s, timezone=%s, default_model=%s, preferences=%s::jsonb, updated_at=now() where user_id=%s", (request.display_name, request.timezone, request.default_model, __import__('json').dumps(request.preferences), user_id))
        conn.commit()
    return {"ok": True}


@router.put("/credentials")
def upsert_credential(request: CredentialUpdate, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        existing = conn.execute("select id, secret_id from public.user_credentials where user_id=%s and provider=%s and label=%s", (user_id, request.provider, request.label)).fetchone()
        secret_id = existing[1] if existing else None
        if request.secret:
            if secret_id:
                conn.execute("select vault.update_secret(%s,%s,%s,%s)", (secret_id, request.secret, f"aurora:{user_id}:{request.provider}:{request.label}", "AURORA user credential"))
            else:
                secret_id = conn.execute("select vault.create_secret(%s,%s,%s)", (request.secret, f"aurora:{user_id}:{request.provider}:{request.label}", "AURORA user credential")).fetchone()[0]
        if existing:
            conn.execute("update public.user_credentials set secret_id=coalesce(%s,secret_id), metadata=%s::jsonb, updated_at=now() where id=%s", (secret_id, __import__('json').dumps(request.metadata), existing[0]))
        else:
            conn.execute("insert into public.user_credentials (user_id,provider,label,secret_id,metadata) values (%s,%s,%s,%s,%s::jsonb)", (user_id, request.provider, request.label, secret_id, __import__('json').dumps(request.metadata)))
        conn.commit()
    return {"ok": True, "provider": request.provider, "label": request.label, "configured": bool(secret_id)}


@router.delete("/credentials/{provider}/{label}")
def delete_credential(provider: str, label: str, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("delete from public.user_credentials where user_id=%s and provider=%s and label=%s", (user_id, provider, label))
        conn.commit()
    return {"ok": True}