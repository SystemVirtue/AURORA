from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from .core import settings
from .quorum import Contribution, compare_contributions, synthesis_prompt


class ReasoningError(RuntimeError):
    pass


class ReasoningGateway:
    """Provider-neutral gateway for reasoning and embeddings."""

    def _endpoint(self, model: str | None = None) -> tuple[str, str, str, str]:
        selected = model or settings.default_model
        if not selected:
            raise ReasoningError("AURORA_DEFAULT_MODEL is not configured")
        if selected.startswith("openrouter/"):
            return "https://openrouter.ai/api/v1", settings.openrouter_api_key or "", selected.removeprefix("openrouter/"), "openrouter"
        if selected.startswith("openai/"):
            return "https://api.openai.com/v1", settings.openai_api_key or "", selected.removeprefix("openai/"), "openai"
        if settings.openrouter_api_key:
            return "https://openrouter.ai/api/v1", settings.openrouter_api_key, selected, "openrouter"
        return "https://api.openai.com/v1", settings.openai_api_key or "", selected, "openai"

    async def complete(self, *, question: str, context: str = "", model: str | None = None) -> dict[str, Any]:
        base, key, actual_model, provider = self._endpoint(model)
        if not key:
            raise ReasoningError("No API key configured for the selected provider")
        system = (
            "You are an AURORA reasoning contributor. Separate supported claims from uncertainty. "
            "Never imply that a model assertion is independently verified. Return a concise answer "
            "and explicitly state material uncertainty."
        )
        prompt = question if not context else f"Evidence/context:\n{context}\n\nQuestion:\n{question}"
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": actual_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
            )
        if response.is_error:
            raise ReasoningError(f"Provider error {response.status_code}: {response.text[:500]}")
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return {"model": actual_model, "provider": provider, "response": text, "latency_ms": round((time.perf_counter() - started) * 1000), "raw": data}

    def _quorum_models(self, requested: str | None) -> list[str]:
        configured = os.getenv("AURORA_QUORUM_MODELS", "").strip()
        models = [item.strip() for item in configured.split(",") if item.strip()]
        if requested and requested not in models:
            models.insert(0, requested)
        if not models and settings.default_model:
            models = [settings.default_model]
        return list(dict.fromkeys(models))[:3]

    async def _quorum_reason(
        self,
        *,
        question: str,
        context: list[dict[str, Any]],
        model: str | None,
        mode: str,
        warrant: str,
    ) -> dict[str, Any]:
        models = self._quorum_models(model)
        if not models:
            raise ReasoningError("No QUORUM models configured")
        started_at = datetime.now(UTC)
        context_text = "\n\n".join(
            f"[Evidence {item.get('evidence_id', 'unknown')}] {item.get('content', '')}" for item in context
        )

        async def contribute(selected: str) -> tuple[str, dict[str, Any] | None, str | None]:
            try:
                result = await self.complete(question=question, context=context_text, model=selected)
                return selected, result, None
            except ReasoningError as exc:
                return selected, None, str(exc)

        results = await asyncio.gather(*(contribute(selected) for selected in models))
        evidence_ids = tuple(str(item["evidence_id"]) for item in context if item.get("evidence_id"))
        contributions = tuple(
            Contribution(model_id=selected, response=result["response"], provider=result["provider"], evidence_ids=evidence_ids)
            for selected, result, error in results if result is not None
        )
        errors = [{"model": selected, "error": error} for selected, _, error in results if error]
        if not contributions:
            raise ReasoningError("All QUORUM contributors failed: " + str(errors))
        deliberation = compare_contributions(question, contributions)
        prompt = synthesis_prompt(question, deliberation)
        synthesis = await self.complete(question=prompt, context="", model=contributions[0].model_id)
        completed_at = datetime.now(UTC)
        return {
            "model": synthesis["model"], "provider": synthesis["provider"], "answer": synthesis["response"],
            "confidence": None,
            "latency_ms": sum(result["latency_ms"] for _, result, _ in results if result is not None) + synthesis["latency_ms"],
            "estimated_cost": None, "started_at": started_at, "completed_at": completed_at,
            "event_time": completed_at, "mode": mode, "raw": synthesis["raw"],
            "quorum": {
                "warrant": warrant,
                "contributors": [
                    {
                        "model": c.model_id,
                        "provider": c.provider,
                        "response": c.response,
                        "evidence_ids": list(c.evidence_ids),
                        "latency_ms": next(result["latency_ms"] for selected, result, _ in results if selected == c.model_id and result is not None),
                    }
                    for c in contributions
                ],
                "failed_contributors": errors,
                "agreement": deliberation.agreement,
                "disagreements": list(deliberation.disagreements),
                "evidence_coverage": deliberation.evidence_coverage,
                "collective_gain": deliberation.collective_gain,
                "synthesis_model": synthesis["model"],
                "synthesis_provider": synthesis["provider"],
                "synthesis_latency_ms": synthesis["latency_ms"],
            },
        }

    async def reason(
        self,
        *,
        question: str,
        context: list[dict[str, Any]] | None = None,
        model: str | None = None,
        mode: str = "balanced",
        warrant: str | None = None,
    ) -> dict[str, Any]:
        """Execute reasoning; spend extra calls only when the caller supplies a warrant."""
        started_at = datetime.now(UTC)
        context = context or []
        if mode not in {"fast", "balanced", "deep", "quorum"}:
            raise ReasoningError(f"Unsupported reasoning mode: {mode}")
        if mode in {"quorum", "deep"} or (mode == "balanced" and not context):
            selected_warrant = warrant or ("explicit_quorum_mode" if mode == "quorum" else "missing_evidence")
            return await self._quorum_reason(
                question=question, context=context, model=model, mode=mode, warrant=selected_warrant,
            )
        context_text = "\n\n".join(f"[Evidence {item.get('evidence_id', 'unknown')}] {item.get('content', '')}" for item in context)
        result = await self.complete(question=question, context=context_text, model=model)
        completed_at = datetime.now(UTC)
        return {
            "model": result["model"], "provider": result["provider"], "answer": result["response"],
            "confidence": None, "latency_ms": result["latency_ms"], "estimated_cost": None,
            "started_at": started_at, "completed_at": completed_at, "event_time": completed_at,
            "mode": mode, "raw": result["raw"], "quorum": None,
        }

    async def embed(self, texts: list[str], model: str | None = None) -> dict[str, Any]:
        """Create embeddings through the same provider boundary."""
        if not texts:
            return {"model": model or settings.embedding_model, "provider": None, "embeddings": []}
        if model:
            actual_model = model.removeprefix("openrouter/").removeprefix("openai/")
            if model.startswith("openrouter/"):
                provider, key, base = "openrouter", settings.openrouter_api_key, "https://openrouter.ai/api/v1"
            else:
                provider, key, base = "openai", settings.openai_api_key, "https://api.openai.com/v1"
        elif settings.openrouter_api_key:
            actual_model = settings.embedding_model
            provider, key, base = "openrouter", settings.openrouter_api_key, "https://openrouter.ai/api/v1"
        else:
            actual_model = settings.embedding_model
            provider, key, base = "openai", settings.openai_api_key or "", "https://api.openai.com/v1"
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
        return {"model": actual_model, "provider": provider, "embeddings": [item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])]}
