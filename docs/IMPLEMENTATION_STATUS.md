# AURORA Implementation Status

**Date:** 2026-09-03

## Executable now

| Capability | Status | Notes |
|---|---|---|
| Python package | ✅ | Python 3.11+ baseline |
| FastAPI API | ✅ | health, authenticated sessions, document ingestion, `/v1/ask` |
| Provider-neutral gateway | ✅ | OpenAI-compatible OpenRouter/OpenAI path |
| Persistent sessions/messages | ✅ | user + assistant messages are durable |
| Reasoning run persistence | ✅ | run + contribution + provenance event |
| Event envelope | ✅ | causation/correlation/schema/idempotency fields |
| Canonical cognitive schema | ✅ | workspace, history, knowledge, cognition, reasoning |
| Workspace authentication | ✅ | Supabase JWT subject bound to workspace membership in API |
| Workspace RLS | ✅ schema | membership policies exist and API performs explicit tenant checks |
| Temporal state | ✅ | valid-time + record-time ranges |
| Relationship versioning | ✅ | surrogate IDs + exclusion constraint |
| Facts vs beliefs | ✅ | `state_type` participates in temporal constraint |
| Evidence links | ✅ | candidate claims receive first-class provenance evidence |
| Document ingestion | ✅ | text ingestion + deterministic chunking + candidate claims |
| Lexical retrieval | ✅ | PostgreSQL full-text retrieval over document chunks |
| Hybrid retrieval | ✅ | lexical + pgvector semantic results fused by reciprocal rank |
| pgvector projection | ✅ | embeddings are nullable/rebuildable; backfill endpoint added |
| Epistemic gaps | ✅ initial | missing-evidence gap emitted when retrieval returns none |
| Conversation normalization | ✅ | ChatGPT, Claude, Gemini and generic structures have adapters |
| Candidate claims | ✅ primitive | conservative extraction; promotion remains explicitly gated |
| Contradiction detection | ✅ | canonical competing-claim pairs exposed through API/UI |
| Belief revision | ✅ initial | authenticated review endpoint + temporal belief versions + audit event |
| QUORUM substrate | ✅ | contribution preservation/comparison; orchestration remains next |
| Portable state bundle | ✅ improved | deterministic ordering + SHA-256 verification + workspace exporter primitive |
| Inspection UI | ✅ initial | authenticated evidence and contradiction inspection |
| Local deployment | ✅ | Supabase CLI + scripts |
| Remote migration deployment | ✅ | dry-run then push |
| CI | 🟡 | Supabase reset passed in prior run; latest Python lint repair is running |

## Current cognitive path

A real request can now follow:

**ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER**

The path includes authenticated tenant enforcement, lexical/semantic retrieval, persistent reasoning contributions, first-class evidence IDs, candidate claim capture, contradiction detection, temporal reviewable beliefs and explicit epistemic gaps. Model assertions remain attributed contributions rather than automatic facts.

## Continuity invariant

Essential cognitive state is portable independently of the runtime, model provider, UI or machine. The state bundle records authoritative tables with deterministic JSON ordering and checksums. Retrieval embeddings remain derived/rebuildable rather than authoritative cognitive state.

## Next execution blocks

1. Verify the current CI run and fix any remaining defects before deployment.
2. Add richer belief-review tests, including contradiction → contested belief → revised belief history.
3. Add authenticated workspace state export/import with dependency-aware restore and dry-run validation.
4. Expand inspection UI from contradictions into claim → evidence → event → reasoning-run provenance graphs.
5. Add selective QUORUM orchestration only for disagreement, uncertainty or consequential questions.
6. Measure collective gain against single-model baselines rather than assuming more models are better.
7. Run a fresh-database reincarnation test: ingest → ask → evidence → reasoning → export → empty DB → import → ask again.
8. Complete the end-to-end MVP audit.

## Explicitly deferred

3D UNBOX environment, distributed agent swarm, autonomous self-modification, Kubernetes, enterprise RBAC, billing, marketplace, IDE plugins, NATS everywhere, huge ontology, autonomous web agent and self-training are design targets only, not MVP implementation requirements.

## Verification policy

Every migration must pass `supabase db reset` locally/CI before remote deployment. Remote changes use migration files and `supabase db push`; direct remote schema edits create migration drift.

A failed CI check is treated as an engineering defect, not ignored.
