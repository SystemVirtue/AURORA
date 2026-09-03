from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from aurora.quorum import Contribution, compare_contributions

_STOPWORDS = {"the", "and", "that", "this", "with", "from", "were", "was", "are", "for", "into"}


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    question: str
    gold_evidence_ids: tuple[str, ...]
    gold_claim_terms: tuple[str, ...]
    unsupported_terms: tuple[str, ...]
    baseline: Contribution
    contributors: tuple[Contribution, ...]
    synthesis: str
    expected_disagreement: bool = False


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if t not in _STOPWORDS}


def _coverage(ids: Sequence[str], gold: Sequence[str]) -> float:
    gold_set = set(gold)
    return 1.0 if not gold_set else len(set(ids) & gold_set) / len(gold_set)


def _unsupported_rate(text: str, unsupported_terms: Sequence[str]) -> float:
    text_lower = text.lower()
    terms = {t.lower() for t in unsupported_terms}
    return 0.0 if not terms else len([t for t in terms if t in text_lower]) / len(terms)


def evaluate_case(case: BenchmarkCase) -> dict[str, float | bool | str]:
    deliberation = compare_contributions(case.question, case.contributors)
    all_ids = tuple(dict.fromkeys(e for c in case.contributors for e in c.evidence_ids))
    baseline_coverage = _coverage(case.baseline.evidence_ids, case.gold_evidence_ids)
    quorum_coverage = _coverage(all_ids, case.gold_evidence_ids)
    baseline_unsupported = _unsupported_rate(case.baseline.response, case.unsupported_terms)
    quorum_unsupported = _unsupported_rate(case.synthesis, case.unsupported_terms)
    claim_tokens = _tokens(" ".join(case.gold_claim_terms))
    synthesis_tokens = _tokens(case.synthesis)
    claim_coverage = 1.0 if not claim_tokens else len(claim_tokens & synthesis_tokens) / len(claim_tokens)
    disagreement_preserved = bool(deliberation.disagreements) == case.expected_disagreement
    baseline_quality = baseline_coverage + claim_coverage - baseline_unsupported
    quorum_quality = quorum_coverage + claim_coverage - quorum_unsupported
    return {
        "case_id": case.case_id,
        "baseline_evidence_coverage": round(baseline_coverage, 4),
        "quorum_evidence_coverage": round(quorum_coverage, 4),
        "evidence_coverage_gain": round(quorum_coverage - baseline_coverage, 4),
        "baseline_unsupported_rate": round(baseline_unsupported, 4),
        "quorum_unsupported_rate": round(quorum_unsupported, 4),
        "unsupported_rate_improvement": round(baseline_unsupported - quorum_unsupported, 4),
        "claim_coverage": round(claim_coverage, 4),
        "disagreement_preserved": disagreement_preserved,
        "lexical_collective_gain": deliberation.collective_gain,
        "quality_delta": round(quorum_quality - baseline_quality, 4),
    }


def default_cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            "agreement_strong_evidence", "When did Project Aurora launch?", ("e1",),
            ("Aurora", "launch", "2024"), ("2025",),
            Contribution("baseline", "Project Aurora launched in 2024.", evidence_ids=("e1",)),
            (Contribution("a", "Project Aurora launched in 2024.", evidence_ids=("e1",)),
             Contribution("b", "Project Aurora launched in 2024.", evidence_ids=("e1",))),
            "The supplied evidence supports a 2024 launch.",
        ),
        BenchmarkCase(
            "complementary_evidence", "What caused the outage?", ("e2", "e3"),
            ("outage", "database", "connection"), (),
            Contribution("baseline", "The outage was caused by a database connection failure.", evidence_ids=("e2",)),
            (Contribution("a", "The outage involved database saturation.", evidence_ids=("e2",)),
             Contribution("b", "The outage involved a connection-pool failure.", evidence_ids=("e3",))),
            "The evidence indicates both database saturation and a connection-pool failure contributed to the outage.",
            True,
        ),
        BenchmarkCase(
            "missing_evidence", "Who approved the change?", (),
            ("approved",), ("Jordan", "Smith"),
            Contribution("baseline", "I cannot determine who approved the change.", evidence_ids=()),
            (Contribution("a", "There is not enough evidence to identify an approver.", evidence_ids=()),
             Contribution("b", "The available material does not identify an approver.", evidence_ids=())),
            "There is insufficient evidence to identify who approved the change.",
        ),
        BenchmarkCase(
            "unsupported_claim_rejected", "Was the migration risk-free?", ("e4",),
            ("migration", "risk"), ("risk-free", "guaranteed"),
            Contribution("baseline", "The migration was risk-free and guaranteed safe.", evidence_ids=("e4",)),
            (Contribution("a", "The migration completed successfully; the evidence does not establish zero risk.", evidence_ids=("e4",)),
             Contribution("b", "The migration completed, but risk-free is unsupported.", evidence_ids=("e4",))),
            "The migration completed successfully, but the supplied evidence does not establish that it was risk-free or guaranteed safe.",
        ),
        BenchmarkCase(
            "conclusion_changes", "Is the old configuration still active?", ("e5", "e6"),
            ("configuration", "active", "replaced"), (),
            Contribution("baseline", "Yes, the old configuration is still active.", evidence_ids=("e5",)),
            (Contribution("a", "The old configuration was active previously.", evidence_ids=("e5",)),
             Contribution("b", "A later record says the old configuration was replaced.", evidence_ids=("e6",))),
            "The later evidence indicates the old configuration was replaced, so the earlier record should not be treated as current.",
            True,
        ),
    )


def run_benchmark(cases: Sequence[BenchmarkCase] | None = None) -> dict:
    cases = tuple(cases or default_cases())
    results = [evaluate_case(case) for case in cases]

    def mean(key: str) -> float:
        return round(sum(float(r[key]) for r in results) / len(results), 4)

    return {
        "cases": len(results),
        "results": results,
        "aggregate": {
            "baseline_evidence_coverage": mean("baseline_evidence_coverage"),
            "quorum_evidence_coverage": mean("quorum_evidence_coverage"),
            "evidence_coverage_gain": mean("evidence_coverage_gain"),
            "baseline_unsupported_rate": mean("baseline_unsupported_rate"),
            "quorum_unsupported_rate": mean("quorum_unsupported_rate"),
            "unsupported_rate_improvement": mean("unsupported_rate_improvement"),
            "claim_coverage": mean("claim_coverage"),
            "disagreement_preservation": round(sum(bool(r["disagreement_preserved"]) for r in results) / len(results), 4),
            "quality_delta": mean("quality_delta"),
        },
        "interpretation": "Lexical collective gain is diagnostic only; quality is evaluated independently against the single-model baseline.",
    }
