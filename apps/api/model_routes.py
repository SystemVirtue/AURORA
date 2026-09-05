from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models")
async def list_models(provider: str = "openrouter", free_only: bool = True) -> dict:
    """Return a live provider catalogue for explicit AURORA model selection.

    OpenRouter's catalogue is intentionally fetched at request time because the
    free-model roster changes. Only models whose current prompt and completion
    pricing are zero are returned when free_only is true.
    """
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
        if free_only and not (prompt in {"0", "0.0", "0.00"} and completion in {"0", "0.0", "0.00"}):
            continue
        models.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or item.get("id"),
                "provider": "openrouter",
                "cost": {"input": prompt, "output": completion, "currency": "USD_per_token"},
                "context_length": item.get("context_length"),
                "architecture": item.get("architecture"),
                "supported_parameters": item.get("supported_parameters", []),
                "free": prompt in {"0", "0.0", "0.00"} and completion in {"0", "0.0", "0.00"},
            }
        )
    models.sort(key=lambda model: (str(model.get("name") or "").lower(), str(model.get("id") or "")))
    return {"provider": "openrouter", "free_only": free_only, "count": len(models), "models": models}
