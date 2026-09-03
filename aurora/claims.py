from __future__ import annotations

import re
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateClaim:
    subject: str
    predicate: str
    object: str
    excerpt: str
    confidence: float


_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def extract_candidate_claims(text: str, *, max_claims: int = 12) -> list[CandidateClaim]:
    """Conservatively extract reviewable candidate claims; never promote them to facts."""
    claims: list[CandidateClaim] = []
    for sentence in _SENTENCE.split(text.strip()):
        sentence = sentence.strip()
        if len(sentence) < 12:
            continue
        words = sentence.split()
        if len(words) < 4:
            continue
        subject_end = min(4, len(words) - 2)
        subject = " ".join(words[:subject_end]).strip(" ,:;")
        remainder = " ".join(words[subject_end:])
        parts = re.split(
            r"\s+(?:is|are|was|were|has|have|had|uses|contains|supports|requires|means)\s+",
            remainder,
            maxsplit=1,
            flags=re.I,
        )
        if len(parts) == 2:
            predicate = "is"
            obj = parts[1].strip(" .")
        else:
            predicate = "asserts"
            obj = remainder.strip(" .")
        if not obj:
            continue
        claims.append(CandidateClaim(subject, predicate, obj, sentence, 0.35))
        if len(claims) >= max_claims:
            break
    return claims


def claim_key(claim: CandidateClaim) -> str:
    return f"{claim.subject.lower()}|{claim.predicate.lower()}|{claim.object.lower()}"


def persist_candidate_claims(
    conn,
    *,
    workspace_id: uuid.UUID,
    source_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    text: str,
) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for candidate in extract_candidate_claims(text):
        claim_id = uuid.uuid4()
        conn.execute(
            """insert into public.claims
               (id,workspace_id,source_id,event_id,subject,predicate,object,assertion_status,confidence,metadata)
               values (%s,%s,%s,%s,%s,%s,%s,'unverified',%s,%s::jsonb)""",
            (
                claim_id,
                workspace_id,
                source_id,
                event_id,
                candidate.subject,
                candidate.predicate,
                candidate.object,
                candidate.confidence,
                '{"extraction":"deterministic_candidate"}',
            ),
        )
        ids.append(claim_id)
    return ids
