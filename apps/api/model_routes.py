# ruff: noqa
from __future__ import annotations

import httpx
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aurora.cognition import merge_retrieval_results, retrieve_lexical
from aurora.core import settings

router = APIRouter(prefix="/v1", tags=["models"])
bearer = HTTPBearer(auto_error=False)


@router.get("/models")
async def list_models(provider: str = "openrouter", free_only: bool = True) -> dict:
    """Return a live provider catalogue for explicit AURORA model selection."""
    if provider != "openrouter":
        raise HTTPException(400, "Server-side model catalogue currently supports openrouter only")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "OpenRouter model catalogue unavailable") from exc

    models = []
    for item in payload.get("data", []):
        pricing = item.get("pricing") or {}
        prompt = str(pricing.get("prompt", ""))
        completion = str(pricing.get("completion", ""))
        is_free = prompt in {"0", "0.0", "0.00"} and completion in {"0", "0.0", "0.00"}
        if free_only and not is_free:
            continue
        models.append({
            "id": item.get("id"), "name": item.get("name") or item.get("id"),
            "provider": "openrouter",
            "cost": {"input": prompt, "output": completion, "currency": "USD_per_token"},
            "context_length": item.get("context_length"),
            "architecture": item.get("architecture"),
            "supported_parameters": item.get("supported_parameters", []),
            "free": is_free,
        })
    models.sort(key=lambda model: (str(model.get("name") or "").lower(), str(model.get("id") or "")))
    return {"provider": "openrouter", "free_only": free_only, "count": len(models), "models": models}


@router.get("/retrieval")
def retrieval(
    workspace_id: str,
    question: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """Authenticated lexical retrieval for browser-executed providers such as Puter."""
    from apps.api.main import current_user

    user_id = current_user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    try:
        with psycopg.connect(settings.database_url) as conn:
            member = conn.execute(
                "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
                (workspace_id, user_id),
            ).fetchone()
            if not member:
                raise HTTPException(403, "User is not a member of this workspace")
            lexical = retrieve_lexical(conn, workspace_id=workspace_id, question=question)
            retrieved = merge_retrieval_results(lexical, [], limit=8)
    except psycopg.Error as exc:
        raise HTTPException(503, "Workspace retrieval failed") from exc
    return {"workspace_id": workspace_id, "question": question, "evidence": retrieved}
