# AURORA Implementation Status

**Date:** 2026-09-03

## Executable now

| Capability | Status | Notes |
|---|---|---|
| Python package | ✅ | Python 3.11+ baseline |
| FastAPI API | ✅ | health, sessions, document ingestion, `/v1/ask` |
| Provider-neutral gateway | ✅ | OpenAI-compatible OpenRouter/OpenAI path |
| Persistent sessions/messages | ✅ | user + assistant messages are durable |
| Reasoning run persistence | ✅ | run + contribution + provenance event |
| Event envelope | ✅ | causation/correlation/schema/idempotency fields |
| Canonical cognitive schema | ✅ | workspace, history, knowledge, cognition, reasoning |
| Workspace RLS | ✅ schema | membership policies exist; API service identity enforcement remains to be completed |
| Temporal state | ✅ | valid-time + record-time ranges |
| Relationship versioning | ✅ | surrogate IDs + exclusion constraint |
| Facts vs beliefs | ✅ | `state_type` participates in temporal constraint |
| Evidence links | ✅ schema | claim/evidence implementation now being activated |
| Document ingestion | ✅ | text ingestion + deterministic chunking |
| Lexical retrieval | ✅ | PostgreSQL full-text retrieval over document chunks |
| Hybrid retrieval | ✅ | lexical + pgvector semantic results fused by reciprocal rank |
| pgvector projection | ✅ | embeddings are nullable/rebuildable; backfill endpoint added |
| Epistemic gaps | ✅ initial | missing-evidence gap emitted when retrieval returns none |
| Conversation normalization | ✅ | ChatGPT, Claude, Gemini and generic structures have adapters |
| Candidate claims | ✅ primitive | conservative extraction + provenance-ready schema; promotion remains gated |
| QUORUM substrate | ✅ | contribution preservation/comparison; orchestration remains next |
| Portable state bundle | ✅ primitive | database-wide exporter/importer remains next |
| Local deployment | ✅ | Supabase CLI + scripts |
| Remote migration deployment | ✅ | dry-run then push |
| CI | 🟢 | latest Python lint/tests pass; Supabase migration validation is running |

## Current cognitive path

A real request can now follow the first meaningful portion of:

**ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER**

The path now includes lexical/semantic retrieval, persistent reasoning contributions, evidence metadata, candidate claim capture and explicit epistemic gaps. Candidate claims remain unverified by design.

## Next execution blocks

1. Activate claim/evidence links during ingestion and reasoning.
2. Add authenticated user identity to the API and bind workspace access to that identity.
3. Add contradiction detection and belief revision workflows.
4. Complete portable database export/import with checksums, ordering and dependency-aware restore.
5. Build evidence/claim/reasoning inspection UI.
6. Add real selective QUORUM orchestration and measure whether additional models improve the answer.
7. Add fresh-database reincarnation integration test.
8. Complete the end-to-end MVP audit.

## Explicitly deferred

3D UNBOX environment, distributed agent swarm, autonomous self-modification, Kubernetes, enterprise RBAC, billing, marketplace, IDE plugins, NATS everywhere, huge ontology, autonomous web agent and self-training are design targets only, not MVP implementation requirements.

## Verification policy

Every migration must pass `supabase db reset` locally/CI before remote deployment. Remote changes use migration files and `supabase db push`; direct remote schema edits create migration drift.

A failed CI check is treated as an engineering defect, not ignored.
