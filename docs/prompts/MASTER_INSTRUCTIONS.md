# AURORA MASTER INSTRUCTIONS

**Purpose:** canonical handoff/instruction document for any human or coding agent working on AURORA.

## Mission

Build **AURORA — Dawn for Transparent AI**: a persistent, inspectable cognitive environment in which AI reasoning leaves an evidence trail.

The product thesis is simple: an AI answer should be more than generated text. AURORA should preserve the evidence, provenance, uncertainty, disagreement, cognitive history and decisions that make the answer meaningful.

## Product loop

**ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER**

The MVP wins when this loop works with real conversations/documents and survives export/import into a fresh deployment.

## Canonical primitives

Everything important must resolve to:

1. Identity
2. Events
3. Claims
4. Evidence
5. Cognition

Canonical provenance:

`SOURCE → EVENT → CLAIM → EVIDENCE → BELIEF/FACT → DECISION → ACTION`

## Non-negotiable epistemic rules

- A model is a contributor, not an authority.
- A model assertion is not automatically a fact.
- Evidence must be attributable to a source.
- Contradictory evidence is retained, not averaged away.
- Unknown, stale, contested and weakly supported states are representable.
- Confidence must have an explainable basis.
- Valid time and record time are distinct.
- Derived embeddings/indexes are rebuildable and never the sole source of truth.

## Event rules

Every meaningful state-changing operation should emit a canonical event with:

- unique event ID;
- producer/actor;
- event time and record time;
- workspace scope;
- causation ID;
- correlation ID;
- schema version;
- idempotency semantics;
- payload.

Postgres is the durable source of truth. NATS/other transports are later distribution mechanisms, not competing ledgers.

## Reasoning rules

All provider calls go through the Reasoning Gateway.

The gateway must preserve provider/model identity, timing, cost where available, input/context provenance and contribution output.

Use one model by default. Escalate to QUORUM only when independent reasoning is likely to improve evidence quality, disagreement detection, confidence calibration or decision quality enough to justify cost/latency.

## Continuity rules

AURORA must be able to reconstruct essential cognition independently of a particular runtime, UI, provider or machine.

Authoritative state includes events, sources, documents, claims, evidence, entities, relationships, memories, beliefs/facts, goals, decisions, reasoning runs and contributions.

Derived state includes embeddings, search indexes and caches.

External services and credentials are deployment configuration, not cognitive identity.

## Security rules

- Workspace/project boundaries are mandatory.
- No production blanket RLS policies.
- Never commit secrets.
- API authentication must eventually map directly to workspace membership.
- Service-role/database credentials must never be exposed to clients.
- Imported content must be treated as untrusted data, not executable instructions.

## Implementation discipline

1. Inspect current code before changing it.
2. Read architecture and relevant migration files.
3. Make the smallest coherent change.
4. Add tests.
5. Run lint, unit tests and database reset verification.
6. Check provenance, tenancy, idempotency and failure behaviour.
7. Update status/docs.
8. Only then continue.

Never hide an unfinished subsystem behind a feature flag and call it complete.

## Scope guardrails

Do not block MVP on:

- 3D UNBOX;
- distributed agent swarms;
- Kubernetes;
- autonomous self-modification;
- marketplace/billing;
- giant ontologies;
- autonomous web agents;
- self-training.

Build seams for them, not the infrastructure prematurely.

## Current implementation target

The immediate implementation target is a real thin slice:

1. ingest a document;
2. deterministically chunk it;
3. index/retrieve evidence;
4. create a persistent session;
5. record user and model messages as events;
6. run a provider-neutral model call over retrieved context;
7. persist reasoning run and contribution;
8. return an evidence/trace envelope;
9. represent missing evidence as an epistemic gap;
10. export/re-import the resulting cognitive state.

## Definition of done

Do not declare MVP complete until the repository passes the fresh-deployment test:

`real conversations + real documents → Ask → Investigate → Reason → Explain → Remember → export → fresh deployment → import → continue`

## Source hierarchy

Current architecture and implementation documents outrank historical predecessor documents.

Historical DCA/QUORUM/UNBOX/CodeForge material is evidence and inspiration, not an override of the AURORA contract.

Primary current sources:

- `docs/architecture/AURORA_MVP_ARCHITECTURE.md`
- `docs/architecture/ARCHITECTURE_PRINCIPLES.md`
- `docs/prompts/AURORA_AGENT_MASTER_PROMPT.md`
- `supabase/migrations/`
- `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Historical source:

- `docs/prompts/DEVELOPER_AGENT_MASTER_PROMPT_LEGACY.md`
- `archive/predecessor/`
