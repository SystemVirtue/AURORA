from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Contribution:
    model_id: str
    response: str
    confidence: float | None = None


@dataclass(frozen=True)
class Deliberation:
    question: str
    contributions: tuple[Contribution, ...]
    agreement: float
    disagreements: tuple[str, ...]


def compare_contributions(question: str, contributions: Sequence[Contribution]) -> Deliberation:
    """Record independent contributions without pretending lexical agreement equals truth.

    This is deliberately a deterministic substrate primitive. Model-based evaluation and
    synthesis belong in the Reasoning Gateway/evaluator layer.
    """
    if not contributions:
        raise ValueError("QUORUM requires at least one contribution")
    normalized = [set(c.response.lower().split()) for c in contributions]
    if len(normalized) == 1:
        agreement = 1.0
    else:
        pairs = []
        for i, left in enumerate(normalized):
            for right in normalized[i + 1 :]:
                union = left | right
                pairs.append(len(left & right) / len(union) if union else 1.0)
        agreement = sum(pairs) / len(pairs)
    disagreements = tuple(
        f"{contributions[i].model_id} vs {contributions[j].model_id}: inspect independently"
        for i in range(len(contributions))
        for j in range(i + 1, len(contributions))
        if contributions[i].response.strip() != contributions[j].response.strip()
    )
    return Deliberation(question, tuple(contributions), round(agreement, 4), disagreements)
