from datetime import datetime

import pytest

from aurora.gateway import ReasoningError, ReasoningGateway


@pytest.mark.asyncio
async def test_reason_normalizes_provider_response(monkeypatch):
    async def fake_complete(*, question, context="", model=None):
        assert question == "What is AURORA?"
        assert "Evidence e1" in context
        assert model == "test-model"
        return {
            "model": "test-model",
            "provider": "test",
            "response": "AURORA is an inspectable cognitive workspace.",
            "latency_ms": 12,
            "raw": {"fixture": True},
        }

    monkeypatch.setattr(ReasoningGateway, "complete", fake_complete)
    result = await ReasoningGateway().reason(
        question="What is AURORA?",
        context=[{"evidence_id": "e1", "content": "AURORA is inspectable."}],
        model="test-model",
        mode="balanced",
    )

    assert result["answer"].startswith("AURORA is")
    assert result["model"] == "test-model"
    assert result["provider"] == "test"
    assert result["latency_ms"] == 12
    assert result["confidence"] is None
    assert isinstance(result["started_at"], datetime)
    assert isinstance(result["completed_at"], datetime)
    assert result["raw"] == {"fixture": True}


@pytest.mark.asyncio
async def test_reason_rejects_unknown_mode():
    with pytest.raises(ReasoningError, match="Unsupported reasoning mode"):
        await ReasoningGateway().reason(question="test", mode="unknown")
