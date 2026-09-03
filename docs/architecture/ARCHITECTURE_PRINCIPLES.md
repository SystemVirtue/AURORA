# AURORA Architectural Principles

These principles are implementation constraints, not marketing language.

## 1. Evidence before confidence

AURORA should distinguish what was said from what is supported.

## 2. History is durable

Meaningful state transitions must be represented in the event history.

## 3. Provenance is first-class

A claim should be traceable to its evidence and source, and a conclusion should be traceable back through the reasoning chain.

## 4. Models are contributors, not authorities

An LLM response is a contribution to cognition. It is not automatically truth.

## 5. Disagreement is information

Conflicting model outputs should be preserved and made inspectable rather than silently collapsed into a vote.

## 6. Uncertainty is state

Unknown, contested, stale and weakly supported knowledge should be representable.

## 7. Time matters

World-validity time and record/observation time must not be conflated.

## 8. Cognition must survive infrastructure

AURORA's essential cognitive state must be portable between deployments, machines and model providers.

## 9. Derived state is disposable

Embeddings, search indexes and caches are rebuildable projections, not the authoritative cognitive record.

## 10. Providers are replaceable

The cognitive substrate must not depend on one LLM vendor or orchestration framework.

## 11. Complexity must earn its place

A capability should be implemented when it improves the demonstrated cognitive loop, not merely because the architecture can accommodate it.

## 12. Real data beats synthetic demos

Development should quickly exercise real conversations, documents, contradictions, provenance and continuity.

## 13. Every capability needs a failure model

An architectural component is incomplete until its failure behaviour, retry/idempotency semantics and observability are understood.

## 14. Security follows the cognitive boundary

Authorization must align with workspace/project ownership and apply consistently to events, claims, evidence, documents, memories and reasoning traces.

## 15. The system must be inspectable by design

AURORA's defining UX is not merely the answer. It is the ability to inspect why the system reached that answer and what remains uncertain.
