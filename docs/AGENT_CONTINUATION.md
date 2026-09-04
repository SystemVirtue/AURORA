# AURORA Agent Continuation Protocol

## Purpose

This file is the machine-readable/human-readable handoff contract for autonomous AURORA development through MVP.

## Standing instruction

> **Proceed as recommended.**

When an authorized continuation agent starts, it must inspect the current repository state, CI state, implementation status, and this protocol before acting. It should execute the highest-value next task required to reach the MVP definition in the canonical architecture documents.

## Stop condition

Autonomous continuation is authorized **only until AURORA MVP is achieved**. Once every MVP acceptance criterion is satisfied and the full CI/E2E verification is green, the agent must stop making implementation changes and report `MVP_ACHIEVED`.

The agent must not autonomously continue into post-MVP features, speculative redesign, production-scale optimization, or unrelated cleanup.

## Operating loop

1. Read this file and `docs/IMPLEMENTATION_STATUS.md`.
2. Read the canonical MVP architecture and architecture principles.
3. Inspect the current Git tree and recent commits.
4. Check CI status and failing tests.
5. Select the smallest high-confidence change that materially advances MVP.
6. Implement the change.
7. Add or update deterministic tests where appropriate.
8. Run the relevant test suite.
9. Commit the change with a descriptive message.
10. Re-evaluate MVP completion.
11. If MVP is not achieved, leave a precise continuation record describing the next recommended action.
12. If MVP is achieved, write `MVP_ACHIEVED` to the continuation state and stop.

## Safety boundaries

The continuation agent may modify source, tests, documentation, CI configuration, and non-secret deployment configuration needed for MVP.

It must not:

- expose, print, commit, or rotate credentials;
- weaken authentication, authorization, tenancy isolation, or provenance controls to make tests pass;
- delete user data or production resources;
- deploy destructive database changes without an explicit migration;
- claim a feature works without test/evidence;
- treat model agreement as proof of truth;
- silently expand MVP scope.

## Definition of done

MVP is achieved only when the canonical MVP acceptance criteria are demonstrably satisfied, including:

- authenticated cognitive workspace;
- real document ingestion;
- persistent conversations and cognitive events;
- lexical/semantic/hybrid retrieval as configured;
- evidence/provenance visibility;
- explicit missing-evidence handling;
- claims and contradiction detection;
- belief/claim review and revision;
- provider-neutral reasoning gateway;
- QUORUM deliberation when warranted;
- persisted contributor/synthesis trace;
- authenticated continuity export/restore and reincarnation verification;
- canonical web UI integrated with the AURORA API and Supabase Auth;
- CI passing, including API QUORUM, continuity, reindex, and benchmark checks;
- deployment path documented and verified to the extent required by MVP.

The architecture may remain intentionally incomplete beyond the cognitive-substrate MVP. That is expected.

## Continuation state

The current state is tracked by the repository itself. Never invent progress. Prefer tests, CI, Git history, and inspected source over assumptions.

When blocked by an external capability unavailable to the agent, record the blocker and stop rather than fabricating completion.
