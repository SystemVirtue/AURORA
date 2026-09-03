import pytest

from aurora.gateway import ReasoningGateway


@pytest.mark.asyncio
async def test_balanced_missing_evidence_escalates_to_quorum(monkeypatch):
    monkeypatch.setenv("AURORA_QUORUM_MODELS", "model-a,model-b")
    calls = []

    async def fake_complete(self, *, question, context="", model=None):
        calls.append((question, model))
        if question.startswith("Synthesize the independent"):
            return {"model": model, "provider": "test", "response": "Synthesis: uncertainty remains.", "latency_ms": 5, "raw": {}}
        return {"model": model, "provider": "test", "response": f"Answer from {model}", "latency_ms": 3, "raw": {}}

    monkeypatch.setattr(ReasoningGateway, "complete", fake_complete)
    result = await ReasoningGateway().reason(question="Unknown?", context=[], mode="balanced")

    assert result["quorum"]["warrant"] == "missing_evidence"
    assert len(result["quorum"]["contributors"]) == 2
    assert result["quorum"]["synthesis_model"] == "model-a"
    assert result["answer"].startswith("Synthesis:")
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_quorum_retains_failed_contributor(monkeypatch):
    monkeypatch.setenv("AURORA_QUORUM_MODELS", "model-a,model-b")

    async def fake_complete(self, *, question, context="", model=None):
        if model == "model-b":
            from aurora.gateway import ReasoningError
            raise ReasoningError("simulated failure")
        return {"model": model, "provider": "test", "response": "A", "latency_ms": 1, "raw": {}}

    monkeypatch.setattr(ReasoningGateway, "complete", fake_complete)
    result = await ReasoningGateway().reason(question="Q", mode="quorum")

    assert len(result["quorum"]["contributors"]) == 1
    assert result["quorum"]["failed_contributors"] == [{"model": "model-b", "error": "simulated failure"}]
