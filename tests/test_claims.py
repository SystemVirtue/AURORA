from aurora.claims import extract_candidate_claims


def test_candidate_claims_are_conservative_and_reviewable() -> None:
    claims = extract_candidate_claims("AURORA is transparent. Evidence supports the claim.\n")
    assert claims
    assert claims[0].confidence < 0.5
    assert claims[0].excerpt


def test_empty_claim_input() -> None:
    assert extract_candidate_claims("") == []
