# Predecessor lineage

AURORA is the clean implementation successor to the earlier SystemVirtue AI architecture work.

Primary predecessor repository:

`SystemVirtue/Supabase_Agentic_Assistant`

That repository contains architectural experiments and implementation attempts around the earlier DCA, QUORUM, UNBOX and CodeForge concepts.

It is intentionally **not copied wholesale into AURORA**.

The predecessor should be treated as an archaeological and R&D layer: useful for recovering ideas, decisions, experiments, failures and lessons, while the AURORA repository maintains a clean implementation boundary.

Key architectural lessons carried forward include:

- canonical event history rather than transient agent state;
- explicit claims and evidence;
- provenance as a graph rather than arrays alone;
- temporal correctness for facts, beliefs and relationships;
- provider-neutral model routing;
- selective multi-model deliberation through QUORUM;
- cognitive continuity across imported conversations;
- portable state and machine reincarnation;
- explicit uncertainty, contradiction and epistemic gaps;
- security/tenancy as a foundational concern rather than a later patch.

The predecessor remains valuable evidence about what has been attempted and what should not be repeated.