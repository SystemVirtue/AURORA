from aurora.evaluation import run_benchmark


def test_collective_gain_benchmark_is_deterministic_and_separates_quality():
    first = run_benchmark()
    second = run_benchmark()
    assert first == second
    assert first["cases"] == 5
    aggregate = first["aggregate"]
    assert aggregate["quorum_evidence_coverage"] >= aggregate["baseline_evidence_coverage"]
    assert aggregate["disagreement_preservation"] == 1.0
    assert aggregate["unsupported_rate_improvement"] > 0
    assert "diagnostic only" in first["interpretation"]
