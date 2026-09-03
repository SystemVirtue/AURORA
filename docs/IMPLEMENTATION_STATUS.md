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
| Workspace RLS | ✅ | membership boundary; no blanket allow policies |
| Temporal state | ✅ | valid-time + record-time ranges |
| Relationship versioning | ✅ | surrogate IDs + exclusion constraint |
| Facts vs beliefs | ✅ | `state_type` participates in temporal constraint |
| Evidence links | ✅ schema | extraction/evaluation layer still evolving |
| Document ingestion | ✅ | text ingestion + deterministic chunking |
| Lexical retrieval | ✅ | PostgreSQL full-text retrieval over document chunks |
| pgvector projection | ✅ schema | embeddings are nullable/rebuildable; semantic generation remains next |
| Epistemic gaps | ✅ initial | missing-evidence gap emitted when retrieval returns none |
| Generic conversation normalization | ✅ | attributed source/role retained |
| QUORUM substrate | ✅ | contribution preservation/comparison; orchestration remains next |
| Portable state bundle | ✅ primitive | database-wide exporter/importer remains next |
| Local deployment | ✅ | Supabase CLI + scripts |
| Remote migration deployment | ✅ | dry-run then push |
| CI | ⚠️ | Supabase job passed; Python lint found and fixed in subsequent commits |

## Current thin slice

A real request can now follow the first meaningful portion of:

**ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER**

Specifically:

1. create or reuse a session;
2. record the user message as an event;
3. retrieve matching document chunks;
4. pass retrieved context through the Reasoning Gateway;
5. persist the reasoning run and model contribution;
6. record the assistant response as an event/message;
7. return evidence metadata and correlation trace;
8. emit an epistemic-gap record when no indexed evidence matches.

This is deliberately a thin slice. It is not yet the full transparent cognitive workspace.

## Remaining MVP work

1. Semantic embedding generation and vector retrieval.
2. Major LLM conversation importers with provenance reconstruction.
3. Atomic claim extraction from documents/conversations/model output.
4. Explicit evidence assessment and claim/evidence graph traversal.
5. Evidence-aware answer presentation and source inspection UI.
6. Authenticated API sessions and end-user RLS integration rather than trusted service/database access.
7. Contradiction detection and belief revision.
8. Full reasoning/evaluation/synthesis provenance.
9. Real selective QUORUM orchestration with measurable collective-gain evaluation.
10. Complete database export/import with checksum verification, ordering and dependency-aware restore.
11. Fresh-deployment reincarnation test.
12. Web UI for the cognitive workspace.

## Verification policy

Every migration must pass `supabase db reset` locally/CI before remote deployment. Remote changes use migration files and `supabase db push`; direct remote schema edits create migration drift.

A failed CI check is treated as an engineering defect, not ignored. The current Python lint failure was caused by Python 3.12 modernization rules and has been corrected in the follow-up commits.
