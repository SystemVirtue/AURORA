# AURORA

## Dawn for Transparent AI

**AURORA is a persistent, inspectable cognitive environment in which AI reasoning leaves an evidence trail.**

AURORA is being built as a transparent cognitive workspace: a place where conversations, documents, claims, evidence, reasoning, decisions and memory remain connected and inspectable over time.

The immediate goal is not to build another chatbot. It is to build a durable cognitive substrate on which increasingly capable AI systems can operate without losing provenance, uncertainty, disagreement or continuity.

## The MVP

> **AURORA — A Transparent Cognitive Workspace**

The MVP should support the complete cognitive loop:

**Ask → Investigate → Reason → Explain → Remember**

A user can:

- converse with AI;
- ingest real documents and files;
- import previous LLM conversations;
- retrieve relevant knowledge and evidence;
- distinguish facts, beliefs and unverified assertions;
- expose contradictions and epistemic gaps;
- use multiple models through a provider-neutral Reasoning Gateway;
- invoke lightweight QUORUM deliberation when it materially improves an answer;
- preserve cognitive history and provenance;
- export and reconstruct the cognitive state on another machine.

## Architectural centre

AURORA is built around five primitives:

1. **Identity**
2. **Events**
3. **Claims**
4. **Evidence**
5. **Cognition**

Everything else sits above these primitives.

A foundational invariant is:

> No higher-order cognitive capability may claim implementation status until its inputs, outputs, provenance, temporal semantics, authorization boundary and failure behaviour are represented in the canonical substrate.

## Canonical provenance

```text
SOURCE → EVENT → CLAIM → EVIDENCE → BELIEF/FACT → DECISION → ACTION
```

The system should be able to traverse this chain in both directions.

## Cognitive continuity

Imported model output is not automatically truth.

For example:

> Claude previously asserted X.

is represented as a model-originated assertion with provenance, not as:

> X is true.

AURORA progressively evaluates assertions into evidence, candidate memories, beliefs or facts according to explicit provenance and confidence rules.

## Machine reincarnation

AURORA treats cognitive portability as an architectural invariant:

> No essential cognitive state may be irreversibly coupled to the lifetime of a particular runtime, server, deployment, model provider, orchestration framework or UI.

A portable state package will allow a fresh deployment to reconstruct an equivalent cognitive state from canonical history, persisted state and source artefacts. Derived indexes and embeddings can be rebuilt; external providers are configuration dependencies rather than cognitive state.

## QUORUM

QUORUM is a capability inside AURORA, not the product itself.

For questions where independent reasoning is useful, AURORA can ask multiple models for hypotheses, compare their evidence and disagreements, evaluate contributions and produce a traceable synthesis.

The system should not force every query through multi-model deliberation. Simple questions should remain cheap and fast; disagreement or consequential uncertainty can trigger deeper reasoning.

## Scope discipline

The MVP deliberately does **not** attempt to implement everything envisioned for the long-term system.

Not MVP:

- 3D UNBOX environment;
- elaborate distributed agent swarms;
- autonomous self-modification;
- Kubernetes-scale orchestration;
- enterprise billing/marketplace infrastructure;
- huge ontology systems;
- autonomous web-agent infrastructure;
- self-training.

These may be designed for, but they do not block the first real cognitive system.

## Lineage

AURORA is the clean implementation successor to earlier SystemVirtue experiments, including the `Supabase_Agentic_Assistant` repository and the QUORUM / UNBOX / CodeForge concepts developed around it.

The predecessor is treated as an **architectural R&D and archaeological layer**, not as a codebase to be copied wholesale. Its experiments, decisions, failures and architectural lessons remain valuable source material.

## Repository structure

```text
apps/             Runtime applications and API/UI entry points
packages/         Cognitive, reasoning, QUORUM and continuity libraries
supabase/         Database migrations and Supabase configuration
tests/            Unit, integration, cognitive, continuity and adversarial tests
fixtures/         Realistic conversations, documents and test datasets
evals/            Capability and regression evaluations
docs/             Architecture and implementation documentation
archive/          Historical lineage and predecessor references
```

## Development principle

**Feature-complete at the cognitive-substrate level, not architecture-complete at the platform level.**

Build the smallest system that genuinely demonstrates transparent, persistent, evidence-linked cognition — then expand it.

## Status

🚧 **Early architecture / bootstrap phase**

The repository is intentionally starting clean. Architecture and implementation will be developed together, with working end-to-end paths and tests preferred over speculative infrastructure.
