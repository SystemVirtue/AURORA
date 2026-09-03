from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Contribution:
    model_id: str
    response: str
    confidence: float | None = None
    provider: str | None = None
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Deliberation:
    question: str
    contributions: tuple[Contribution, ...]
    agreement: float
    disagreements: tuple[str, ...]
    evidence_coverage: float
    collective_gain: float


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in {"the", "and", "that", "this", "with", "from"}}


def should_deliberate(*, mode: str, evidence_count: int, contradiction_count: int = 0) -> tuple[bool, str]:
    """Deterministic MVP policy: spend extra calls only when warranted."""
    if mode == "quorum":
        return True, "explicit_quorum_mode"
    if mode == "deep":
        return True, "deep_reasoning_mode"
    if contradiction_count > 0:
        return True, "workspace_contradiction"
    if evidence_count == 0:
        return True, "missing_evidence"
    return False, "single_model_sufficient"


def compare_contributions(question: str, contributions: Sequence[Contribution]) -> Deliberation:
    """Compare independent contributions without treating agreement as truth."""
    if not contributions:
        raise ValueError("QUORUM requires at least one contribution")
    token_sets = [_tokens(c.response) for c in contributions]
    if len(token_sets) == 1:
        agreement = 1.0
    else:
        pairs = [len(left & right) / len(left | right) if left | right else 1.0 for left, right in combinations(token_sets, 2)]
        agreement = sum(pairs) / len(pairs)
    disagreements = tuple(
        f"{left.model_id} vs {right.model_id}: independent responses differ"
        for left, right in combinations(contributions, 2)
        if left.response.strip() != right.response.strip()
    )
    union_evidence = set().union(*(set(c.evidence_ids) for c in contributions))
    average_evidence = sum(len(c.evidence_ids) for c in contributions) / len(contributions)
    evidence_coverage = min(1.0, len(union_evidence) / max(1.0, average_evidence))
    collective_gain = round(max(0.0, evidence_coverage * (1.0 - agreement)), 4)
    return Deliberation(
        question=question,
        contributions=tuple(contributions),
        agreement=round(agreement, 4),
        disagreements=disagreements,
        evidence_coverage=round(evidence_coverage, 4),
        collective_gain=collective_gain,
    )


def synthesis_prompt(question: str, deliberation: Deliberation) -> str:
    """Create an attribution-preserving synthesis prompt."""
    contributions = "\n\n".join(
        f"MODEL {c.model_id}:\n{c.response}\nEvidence IDs: {', '.join(c.evidence_ids) or 'none'}"
        for c in deliberation.contributions
    )
    return (
        "Synthesize the independent model contributions below for AURORA. "
        "Do not decide truth merely from agreement. Preserve material disagreement, "
        "identify uncertainty, and distinguish evidence-backed statements from model assertions. "
        "Never describe a model assertion as verified fact unless the supplied evidence supports it.\n\n"
        f"Question:\n{question}\n\n{contributions}\n\n"
        f"Measured lexical agreement: {deliberation.agreement}. "
        f"Evidence coverage: {deliberation.evidence_coverage}. "
        f"Collective-gain signal: {deliberation.collective_gain}."
    )
