from __future__ import annotations

import time
from typing import Any

import httpx

from .core import settings


class ReasoningError(RuntimeError):
    pass


class ReasoningGateway:
    """Provider-neutral gateway for reasoning and embeddings."""

    def _endpoint(self, model: str | None = None) -> tuple[str, str, str, str]:
        selected = model or settings.default_model
        if not selected:
            raise ReasoningError("AURORA_DEFAULT_MODEL is not configured")
        if selected.startswith("openrouter/") or settings.openrouter_api_key:
            return (
                "https://openrouter.ai/api/v1",
                settings.openrouter_api_key or "",
                selected.removeprefix("openrouter/"),
                "openrouter",
            )
        return "https://api.openai.com/v1", settings.openai_api_key or "", selected, "openai"

    async def complete(self, *, question: str, context: str = "", model: str | None = None) -> dict[str, Any]:
        base, key, actual_model, provider = self._endpoint(model)
        if not key:
            raise ReasoningError("No API key configured for the selected provider")

        system = (
            "You are an AURORA reasoning contributor. Separate supported claims from "
            "uncertainty. Never imply that a model assertion is independently verified. "
            "Return a concise answer and explicitly state material uncertainty."
        )
        prompt = question if not context else f"Evidence/context:\n{context}\n\nQuestion:\n{question}"
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": actual_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        if response.is_error:
            raise ReasoningError(f"Provider error {response.status_code}: {response.text[:500]}")
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return {
            "model": actual_model,
            "provider": provider,
            "response": text,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "raw": data,
        }

    async def embed(self, texts: list[str], model: str | None = None) -> dict[str, Any]:
        """Create embeddings through the same provider boundary; failures are explicit."""
        if not texts:
            return {"model": model or settings.embedding_model, "provider": None, "embeddings": []}
        if model:
            actual_model = model.removeprefix("openrouter/")
            provider = "openrouter" if model.startswith("openrouter/") else "openai"
            key = settings.openrouter_api_key if provider == "openrouter" else settings.openai_api_key
            base = "https://openrouter.ai/api/v1" if provider == "openrouter" else "https://api.openai.com/v1"
        elif settings.openrouter_api_key:
            actual_model, provider, key, base = settings.embedding_model, "openrouter", settings.openrouter_api_key, "https://openrouter.ai/api/v1"
        else:
            actual_model, provider, key, base = settings.embedding_model, "openai", settings.openai_api_key or "", "https://api.openai.com/v1"
        if not key:
            raise ReasoningError("No API key configured for embeddings")
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base}/embeddings",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": actual_model, "input": texts},
            )
        if response.is_error:
            raise ReasoningError(f"Embedding provider error {response.status_code}: {response.text[:500]}")
        data = response.json()
        return {
            "model": actual_model,
            "provider": provider,
            "embeddings": [item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])],
        }
