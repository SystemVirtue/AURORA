# AURORA Implementation Status

**Date:** 2026-09-03

## MVP progress estimate

**Overall: ~72% toward the defined MVP.** This is a weighted engineering estimate, not a feature-count percentage. The remaining work is concentrated in restore/reincarnation proof, provenance inspection, selective QUORUM and final end-to-end validation.

| Capability | MVP completion | Status | Notes |
|---|---:|---|---|
| Python package | 100% | ✅ | Python 3.11+ baseline |
| FastAPI API | 90% | 🟢 | health, authenticated sessions, ingestion, ask |
| Provider-neutral gateway | 70% | 🟡 | OpenAI-compatible path; richer provider routing remains |
| Persistent sessions/messages | 90% | 🟢 | durable user + assistant history |
| Reasoning persistence | 85% | 🟢 | runs, contributions, provenance events |
| Canonical cognitive schema | 95% | 🟢 | core workspace/history/knowledge/cognition/reasoning substrate |
| Workspace authentication | 90% | 🟢 | JWT subject + explicit membership checks |
| Workspace RLS | 90% | 🟢 | no blanket policies; API also enforces tenant boundaries |
| Temporal state | 85% | 🟢 | valid-time + record-time ranges |
| Document ingestion | 90% | 🟢 | deterministic chunking + candidate claims |
| Hybrid retrieval | 85% | 🟢 | lexical + pgvector reciprocal-rank fusion |
| Claims + evidence | 80% | 🟢 | first-class provenance; promotion remains gated |
| Contradiction detection | 80% | 🟢 | competing claims exposed through API/UI |
| Belief revision | 75% | 🟢 | authenticated review + temporal belief versions |
| Epistemic gaps | 70% | 🟡 | initial missing-evidence detection; richer gap resolution remains |
| Conversation normalization | 75% | 🟡 | ChatGPT, Claude, Gemini and generic adapters |
| Portable export | 80% | 🟢 | deterministic JSON + SHA-256 + workspace exporter |
| Portable restore | 55% | 🟡 | dependency-aware restore, dry-run validation, auth remapping, derived chunk rebuild |
| Reincarnation proof | 20% | 🔴 | fresh-database end-to-end test still required |
| Inspection UI | 50% | 🟡 | evidence/contradiction inspection; provenance graph next |
| QUORUM | 35% | 🔴 | contribution substrate exists; selective orchestration next |
| Collective-gain evaluation | 10% | 🔴 | baseline/evaluation protocol still required |
| CI / migration verification | 100% | 🟢 | latest Python and Supabase jobs passed |

## Verified CI baseline

Workflow run `33710912476` completed successfully. The Python job passed dependency installation, Ruff and pytest. The Supabase job passed local startup and a complete `supabase db reset`. This is the current correctness baseline.

## Current cognitive path

A real request can now follow:

**ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER**

The path includes authenticated tenant enforcement, lexical/semantic retrieval, persistent reasoning contributions, first-class evidence IDs, candidate claim capture, contradiction detection, temporal reviewable beliefs and explicit epistemic gaps. Model assertions remain attributed contributions rather than automatic facts.

## Continuity implementation

The state continuity layer now has:

- deterministic authoritative-table export;
- stable canonical row ordering;
- SHA-256 manifest verification;
- dependency-aware restore ordering;
- dry-run restore validation;
- explicit cross-workspace rejection;
- explicit auth-user dependency mapping rather than exporting credentials;
- deterministic rebuilding of `document_chunks` from authoritative documents;
- a CLI restore entry point at `scripts/restore-state.py`.

Embeddings remain derived state and are intentionally rebuilt after restoration. Authentication identities remain an external dependency: AURORA preserves their references but does not export credentials or attempt to clone `auth.users`.

## Next execution blocks

1. Add a real fresh-database reincarnation integration test: ingest → ask → review → export → empty DB → map auth identity → import → rebuild chunks → reindex embeddings → ask again.
2. Verify restored event/message/claim/evidence/belief/reasoning counts and provenance equivalence.
3. Expand inspection UI into claim → evidence → event → reasoning-run provenance graphs.
4. Add selective QUORUM orchestration only for disagreement, uncertainty or consequential questions.
5. Define and measure collective gain against a single-model baseline.
6. Complete the end-to-end MVP audit and freeze the MVP contract.

## Explicitly deferred

3D UNBOX environment, distributed agent swarm, autonomous self-modification, Kubernetes, enterprise RBAC, billing, marketplace, IDE plugins, NATS everywhere, huge ontology, autonomous web agent and self-training are design targets only, not MVP implementation requirements.

## Verification policy

Every migration must pass `supabase db reset` locally/CI before remote deployment. Remote changes use migration files and `supabase db push`; direct remote schema edits create migration drift.

A failed CI check is treated as an engineering defect, not ignored.
