# AURORA MVP Architecture

**Status:** Foundational architecture contract  
**Product:** AURORA — Dawn for Transparent AI  
**MVP:** A Transparent Cognitive Workspace

## 1. Purpose

AURORA is a persistent, inspectable cognitive environment in which AI reasoning leaves an evidence trail.

The MVP is deliberately small in infrastructure and ambitious in cognition. It must demonstrate a real, durable cognitive loop rather than a collection of disconnected AI features.

## 2. Core user loop

```text
ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER
```

The system should be able to answer a question using prior conversations and documents, expose the evidence and uncertainty behind the answer, preserve the resulting reasoning/history, and later continue from that state.

## 3. Five primitives

The canonical substrate is built around:

1. Identity
2. Events
3. Claims
4. Evidence
5. Cognition

Higher-order capabilities must depend on these primitives rather than bypass them.

### Architectural invariant

> No higher-order cognitive capability may claim implementation status until its inputs, outputs, provenance, temporal semantics, authorization boundary and failure behaviour are represented in the canonical substrate.

## 4. Canonical cognitive flow

```text
USER / CLIENT
    ↓
INPUT
    ↓
EVENT
    ↓
PERCEPTION / INTERPRETATION
    ↓
WORLD / KNOWLEDGE STATE
    ├── CLAIMS
    ├── EVIDENCE
    ├── ENTITIES / RELATIONSHIPS
    └── FACTS / BELIEFS
    ↓
MEMORY
    ↓
GOALS / TASKS
    ↓
META-COGNITION
    ↓
REASONING GATEWAY
    ↓
REASONING / DELIBERATION
    ↓
EVALUATION / ADJUDICATION
    ↓
STATE UPDATE
    ↓
ACTION / RESPONSE
    ↓
OBSERVATION
    ↓
NEW EVENT
```

Not every interaction traverses every stage. The architecture supports progressively deeper cognition without requiring maximum complexity for every query.

## 5. Event ledger

Everything meaningful should produce an event.

The durable event ledger is the canonical history from which cognitive state can be understood and, where necessary, reconstructed.

An event should contain at minimum:

- event_id;
- event_type;
- producer / actor;
- event timestamp;
- record timestamp;
- workspace/project scope;
- aggregate/entity identifiers;
- causation_id;
- correlation_id;
- schema_version;
- payload;
- idempotency semantics.

The initial implementation should use PostgreSQL as the durable source of truth. An outbox can later publish events to NATS JetStream without creating an unsafe dual-write dependency.

## 6. Provenance

Canonical provenance is:

```text
SOURCE → EVENT → CLAIM → EVIDENCE → BELIEF/FACT → DECISION → ACTION
```

The graph must support forward and reverse traversal.

Denormalized arrays may be used as caches or convenience fields, but authoritative relationships should be represented explicitly.

## 7. Claims, facts and beliefs

AURORA must distinguish:

- what a source said;
- what the system currently considers supported;
- what is uncertain or contested;
- what was inferred by a model;
- what a human explicitly asserted.

A model assertion is not automatically a fact.

Example:

```text
Source: Claude
Claim: X
Status: unverified assertion
```

rather than:

```text
X = fact
```

This distinction is central to transparent AI.

## 8. Temporal semantics

Cognitive state needs both:

- **valid time:** when a fact/belief is considered applicable in the represented world;
- **record time:** when AURORA learned or recorded that state.

This should be implemented deliberately rather than labelled "bitemporal" without both dimensions.

Temporal versions of relationships require stable logical identity plus version/interval semantics rather than a simple `(source_id, target_id, rel_type)` primary key.

## 9. Evidence

Evidence is a first-class object.

Evidence should identify its source and relationship to the claim it supports, contradicts, qualifies or contextualizes.

Evidence assessment should preserve:

- provenance;
- source type;
- confidence;
- extraction/derivation method;
- supporting and contradicting relationships;
- temporal relevance.

## 10. Memory

Memory is not a giant JSON blob.

A memory should reference the underlying claims/evidence and record enough metadata to explain why it exists, including confidence, provenance, creation/confirmation history and supersession.

Memory promotion should be a cognitive operation, not an automatic consequence of an LLM response.

## 11. Cognitive continuity

Historical conversations are imported through a canonical pipeline:

```text
RAW IMPORT
 → SOURCE METADATA
 → INTERACTION EVENTS
 → ASSERTIONS / CLAIMS
 → PROVENANCE
 → EVIDENCE ASSESSMENT
 → CANDIDATE MEMORY
 → PROMOTION / REJECTION
```

The MVP should support practical imports from major LLM conversation formats plus a generic importer.

## 12. Reasoning Gateway

All model calls should pass through a provider-neutral gateway.

Initial provider targets may include OpenRouter, OpenAI, Anthropic, Gemini and local Ollama/vLLM deployments.

Routing should eventually consider:

- capability;
- context requirements;
- cost;
- latency;
- reliability;
- modality;
- task suitability;
- model family/version.

The application should not embed provider-specific routing logic in cognitive services.

## 13. QUORUM

QUORUM is an AURORA reasoning capability.

Basic operation:

```text
QUESTION
  ├── MODEL A → hypothesis
  ├── MODEL B → hypothesis
  ├── MODEL C → hypothesis
  └── MODEL D → hypothesis
          ↓
       EVALUATOR
          ↓
  AGREEMENTS / DISAGREEMENTS
  EVIDENCE / UNCERTAINTIES
          ↓
       SYNTHESIS
```

The MVP should preserve independent contributions, evidence references, disagreements, evaluation criteria and synthesis provenance.

AURORA should invoke QUORUM selectively. Simple questions should remain cheap; disagreement, uncertainty or consequential decisions can justify deeper deliberation.

## 14. Epistemic gaps

AURORA should be able to represent:

- missing evidence;
- unresolved contradictions;
- insufficient confidence;
- unanswered questions;
- stale knowledge;
- claims that require verification.

An epistemic gap is useful only if it is actionable: the system should be able to say what is unknown and, where possible, what evidence would reduce the uncertainty.

## 15. Machine reincarnation

Portability is an architectural invariant:

> No essential cognitive state may be irreversibly coupled to the lifetime of a particular runtime, server, deployment, model provider, orchestration framework or UI.

A portable export should contain canonical state and source artefacts, for example:

```text
aurora-export/
├── manifest.json
├── schema/
├── events/
├── conversations/
├── claims/
├── evidence/
├── entities/
├── relationships/
├── memories/
├── goals/
├── tasks/
├── decisions/
├── reasoning_runs/
├── contributions/
├── epistemic_gaps/
├── provenance/
├── documents/
├── embeddings/
└── checksums/
```

Authoritative cognitive state must be separated from derived state. Embeddings, indexes and caches can be rebuilt. Provider credentials and external services are configuration dependencies, not cognitive identity.

## 16. Developmental continuity

Development history can become contextual evidence for future AURORA instances, but it must remain separated from ordinary knowledge.

Suggested namespaces:

```text
AURORA
├── personal
├── projects
│   ├── QUORUM
│   ├── UNBOX
│   └── OBIE
├── research
└── development
    ├── architecture
    ├── experiments
    ├── tests
    ├── failures
    └── decisions
```

Repository/Git ingestion is not required for MVP. The architectural boundary should exist first.

## 17. MVP data model

Keep the initial schema compact.

### Identity

- users
- workspaces
- workspace_members

### History

- events
- sessions
- messages

### Knowledge

- sources
- documents
- claims
- evidence
- entities
- relationships

### Cognition

- memories
- beliefs/facts
- goals
- decisions

### Reasoning

- reasoning_runs
- model_contributions

### Optional early capability

- epistemic_gaps

The exact physical schema may evolve, but these concepts must retain clear ownership and provenance.

## 18. Security and tenancy

The workspace/project boundary must exist before production hardening.

Development-only permissive policies such as `USING (true)` and `WITH CHECK (true)` are not acceptable as the final authorization model.

Every cognitive object must have an explicit authorization boundary or inherit one through a rigorously defined ownership relationship.

## 19. MVP demonstration

The strongest acceptance test is:

1. Import years of AI conversations.
2. Import project documents.
3. Construct claims, evidence and provenance.
4. Ask a question.
5. Retrieve relevant evidence.
6. Reason with one or more models.
7. Expose agreement, disagreement and uncertainty.
8. Produce an answer with traceability.
9. Store the result in cognitive history.
10. Export the complete state.
11. Deploy AURORA on a fresh machine.
12. Import the state.
13. Verify/rebuild derived state.
14. Ask: **"Continue where we left off."**

If this works meaningfully and the answer remains traceable to its sources and prior cognitive state, the MVP has succeeded.

## 20. Explicit non-goals

Do not block MVP on:

- 3D UNBOX;
- distributed agent swarms;
- autonomous self-modification;
- Kubernetes;
- enterprise billing;
- marketplace infrastructure;
- IDE plugins;
- NATS everywhere;
- giant ontologies;
- autonomous web-agent infrastructure;
- self-training.

Design seams for these capabilities; do not implement them prematurely.

## 21. Build philosophy

**Feature-complete at the cognitive-substrate level, not architecture-complete at the platform level.**

The first AURORA should be a real working cognitive system with a small number of strong invariants, not a large architecture diagram with simulated cognition.