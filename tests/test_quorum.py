from aurora.quorum import Contribution, compare_contributions, should_deliberate, synthesis_prompt


def test_simple_evidence_does_not_warrant_quorum():
    assert should_deliberate(mode="balanced", evidence_count=3) == (False, "single_model_sufficient")


def test_missing_evidence_warrants_quorum():
    assert should_deliberate(mode="balanced", evidence_count=0) == (True, "missing_evidence")


def test_contradiction_warrants_quorum():
    assert should_deliberate(mode="balanced", evidence_count=4, contradiction_count=1) == (True, "workspace_contradiction")


def test_disagreement_is_preserved_and_collective_gain_is_measurable():
    deliberation = compare_contributions(
        "What happened?",
        [
            Contribution("model-a", "The event happened in 2024.", evidence_ids=("e1",)),
            Contribution("model-b", "The event happened in 2025.", evidence_ids=("e2",)),
        ],
    )
    assert deliberation.disagreements
    assert deliberation.agreement < 1
    assert 0 <= deliberation.collective_gain <= 1


def test_synthesis_prompt_preserves_epistemic_boundary():
    deliberation = compare_contributions(
        "Is X true?",
        [Contribution("model-a", "X is true", evidence_ids=("e1",))],
    )
    prompt = synthesis_prompt("Is X true?", deliberation)
    assert "Do not decide truth merely from agreement" in prompt
    assert "verified fact" in prompt
