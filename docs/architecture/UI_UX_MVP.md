# AURORA UI/UX MVP — Layered Cognitive Workspace

**Status:** MVP UX direction / implementation contract  
**Date:** 2026-09-06

## 1. Why this document exists

AURORA's backend MVP is substantially complete, but the current web client is a functional inspection console rather than the finished cognitive workspace experience.

The UI must not become a prettier CRUD dashboard. Its job is to make AURORA's distinctive cognitive state understandable and navigable:

- what is happening now;
- what AURORA knows;
- why it believes something;
- what is uncertain or contradictory;
- which models contributed;
- what changed over time;
- what the user has decided or needs to do next.

The UI is therefore an **exploration interface over the cognitive substrate**, not merely a form collection for API endpoints.

## 2. Current frontend assessment

The canonical frontend is `apps/web/index.html`, `apps/web/app.js` and `apps/web/model_access.js`.

It already exposes the major MVP capabilities: authentication, workspaces, ingestion, questioning, evidence, epistemic status, QUORUM, contradiction review, provenance, goals/tasks/decisions, conversation import, continuity and explicit model access.

However, the current presentation is intentionally basic: a long single-page sequence of cards, dense controls, raw trace output and developer-oriented status text. CI validates asset integrity and JavaScript syntax, but does not validate interaction quality or browser behaviour.

Therefore distinguish:

| Dimension | Current assessment |
|---|---:|
| Frontend functional coverage | ~90–95% |
| Cognitive information exposed | ~85–90% |
| Information architecture | ~50% |
| Visual hierarchy | ~45% |
| Interaction design | ~50% |
| Data exploration/navigation | ~35% |
| Provenance visualisation | ~35% |
| Responsive/mobile experience | ~45% |
| Browser E2E validation | ~20% |
| Overall UX/product maturity | ~50–60% |

These are engineering/product estimates, not measured user-research scores.

## 3. Product principle

AURORA should feel like:

> **a cognitive operating environment with a conversational front door and an explorable state space.**

The user should be able to start with a question and progressively descend into its supporting state without leaving the workspace.

The interface should support both:

**CONVERSE** — ask, investigate, reason, act.

and:

**EXPLORE** — inspect sources, claims, evidence, beliefs, events, decisions, tasks, models and provenance.

Neither mode should dominate the other.

## 4. Proposed information architecture

Use a persistent application shell rather than one long document.

```text
AURORA
├── Workspace switcher
├── Global search / command bar
├── New / Ask
│
├── HOME — cognitive overview
│   ├── Active question
│   ├── Recent reasoning
│   ├── Unresolved gaps
│   ├── Contradictions
│   ├── Goals / tasks
│   └── Recent sources
│
├── THINK — reasoning workspace
│   ├── Question
│   ├── Evidence context
│   ├── Warrant
│   ├── Model selection
│   ├── QUORUM
│   ├── Synthesis
│   └── Trace
│
├── KNOWLEDGE — evidence explorer
│   ├── Sources
│   ├── Documents
│   ├── Claims
│   ├── Evidence
│   ├── Contradictions
│   └── Beliefs / facts
│
├── PROVENANCE — causal/explanatory graph
│   ├── Claim → evidence
│   ├── Evidence → source
│   ├── Reasoning → contribution
│   ├── Contribution → synthesis
│   └── Decision/action dependencies
│
├── MEMORY — cognitive history
│   ├── Conversations
│   ├── Events
│   ├── Reasoning runs
│   └── Temporal state
│
├── ACTION — goals / tasks / decisions
│
└── SYSTEM — model access / continuity / workspace settings
```

This is an information architecture target. It does not require implementing every screen before MVP freeze.

## 5. Layered disclosure

AURORA should expose information progressively.

### Layer 0 — answer

The default interaction is simple:

> **Answer**

with compact epistemic badges such as:

`SUPPORTED` · `UNCERTAIN` · `CONTRADICTION` · `MISSING EVIDENCE` · `QUORUM`

### Layer 1 — why

One click reveals:

- evidence used;
- source names;
- confidence/status;
- warrant;
- models used;
- key disagreements.

### Layer 2 — how

Expand the reasoning run:

- contributors;
- synthesis;
- retrieval method;
- latency;
- model/provider;
- epistemic gaps;
- trace/correlation ID.

### Layer 3 — substrate

Open the underlying objects:

- claim;
- evidence record;
- source/document/chunk;
- event;
- belief version;
- reasoning contribution;
- goal/task/decision.

### Layer 4 — provenance graph

Explore causal relationships visually and navigate bidirectionally.

This prevents the primary UI from becoming an unreadable database viewer while retaining forensic depth.

## 6. Dashboard design

The HOME dashboard should answer five questions immediately:

1. **What am I working on?**
2. **What did AURORA just conclude?**
3. **Why does it think that?**
4. **What is unresolved?**
5. **What should I inspect or do next?**

Recommended dashboard zones:

```text
┌───────────────────────────────────────────────────────────┐
│ AURORA   Workspace ▼    Search / Ask…             Profile │
├──────────────┬────────────────────────────────────────────┤
│ NAV          │ ACTIVE COGNITION                            │
│              │                                              │
│ Home         │ Current question / answer                    │
│ Think        │ evidence + epistemic state                   │
│ Knowledge    │                                              │
│ Provenance   ├──────────────────────┬───────────────────────┤
│ Memory       │ UNRESOLVED           │ ACTIVE WORK           │
│ Action       │ contradictions/gaps  │ goals/tasks/decisions │
│ System       ├──────────────────────┴───────────────────────┤
│              │ RECENT COGNITION / SOURCES / EVENTS          │
└──────────────┴────────────────────────────────────────────┘
```

The exact visual treatment can evolve; the persistent hierarchy should not.

## 7. THINK / reasoning workspace

The primary reasoning screen should make the cognitive loop visible without exposing implementation noise.

```text
QUESTION
   ↓
CONTEXT
   ↓
EPISTEMIC STATE / WARRANT
   ↓
REASONING
   ├── Model A
   ├── Model B
   └── Model C
   ↓
COMPARISON
   ↓
SYNTHESIS
   ↓
ANSWER
```

Each stage should be collapsible. The answer remains visually dominant; deeper evidence and reasoning are progressively disclosed.

Model selection should be a deliberate control, not a hidden text input. Free/keyless status, provider and selected model(s) should be visible before execution.

## 8. KNOWLEDGE explorer

The knowledge interface should behave more like an investigative browser than a table dump.

Core pattern:

```text
FILTER / SEARCH
      ↓
OBJECT LIST
      ↓
OBJECT INSPECTOR
      ↓
RELATED OBJECTS
      ↓
PROVENANCE / HISTORY
```

A selected claim should immediately show:

- current status;
- confidence;
- competing claims;
- supporting evidence;
- contradicting evidence;
- source/document/chunk;
- review history;
- beliefs derived from it;
- reasoning runs that used it.

## 9. Provenance explorer

The existing claim-level API should become an interactive graph/relationship inspector.

Minimum MVP graph vocabulary:

`SOURCE → EVENT → CLAIM → EVIDENCE → REASONING RUN → CONTRIBUTION → SYNTHESIS`

and, where available:

`CLAIM → BELIEF/FACT → DECISION → TASK/ACTION`

Every node should be clickable. The graph should support focus mode so users can inspect one causal chain without displaying the entire workspace.

A text relationship list should remain available as an accessibility/debug fallback.

## 10. Global search

AURORA needs one search surface that can find across the cognitive substrate rather than forcing users to know which subsystem contains the object.

Search targets should eventually include:

- conversations/messages;
- documents/chunks;
- claims;
- evidence;
- decisions;
- goals/tasks;
- reasoning runs;
- events.

Results should be grouped by object type and provide direct inspection links.

This can begin as lexical search over the existing retrieval layer and evolve later.

## 11. Data IO / ingestion

Ingestion should be treated as a first-class workflow rather than a textarea hidden halfway down a page.

The user should see:

`IMPORT → PARSE → CHUNK → EXTRACT → VERIFY → AVAILABLE`

For every imported source, show:

- source identity;
- document/message count;
- chunks created;
- candidate claims;
- unverified status;
- import provenance;
- any errors/warnings.

Drag/drop files and conversation imports should converge on the same visible ingestion model.

## 12. Cognitive status language

Avoid developer-centric status as the primary language.

Prefer:

- **Supported by evidence**
- **Needs verification**
- **Conflicting evidence**
- **Insufficient evidence**
- **Model disagreement**
- **Human reviewed**
- **Historical context**

Technical details such as UUIDs, provider IDs and correlation IDs belong in expandable diagnostics.

## 13. Interaction rules

1. Never make the user understand the database schema to use AURORA.
2. Never hide epistemic uncertainty merely to make the answer look confident.
3. Never present a model assertion as a verified fact.
4. Keep primary actions obvious and secondary diagnostics collapsible.
5. Preserve context while navigating into evidence/provenance.
6. Every object that can explain an answer should be reachable from that answer.
7. Every important state transition should provide a path back to its cause.
8. Avoid modal overload; use drawers/panels for inspection where practical.
9. Destructive/irreversible operations require explicit confirmation.
10. The UI must remain usable on a laptop before optimizing for phone layouts.

## 14. MVP implementation sequence

### UX-MVP A — application shell

Replace the long card stack with:

- persistent sidebar;
- top workspace/search bar;
- main content area;
- right inspector/drawer pattern;
- responsive collapse.

### UX-MVP B — Home dashboard

Build a useful landing surface from existing API data:

- active/recent reasoning;
- unresolved contradictions/gaps;
- goals/tasks;
- recent sources;
- quick Ask/Import actions.

### UX-MVP C — Think workspace

Make the current answer/evidence/QUORUM flow the flagship interaction.

### UX-MVP D — Knowledge explorer

Add unified object browsing and search over currently available data.

### UX-MVP E — Provenance inspector

Turn the existing relationship data into a focused interactive exploration view. Start with a dependency-chain layout; a full graph engine is optional until justified.

### UX-MVP F — Data IO centre

Unify document ingestion, conversation import, continuity export/restore and model access under System/Data rather than scattering them through the home page.

### UX-MVP G — browser validation

Add browser-level smoke tests for:

- sign-in;
- workspace selection;
- ingestion;
- Ask;
- evidence expansion;
- QUORUM;
- claim inspection/review;
- action creation;
- import;
- export validation.

## 15. What NOT to do

Do not spend MVP effort on:

- decorative 3D environments;
- animated dashboards with no cognitive value;
- giant node graphs by default;
- replacing the proven backend merely to suit a frontend framework;
- premature component-library churn;
- a large SPA build system solely for visual polish;
- hiding raw evidence behind an opaque AI summary.

The UX should be sophisticated because the information architecture is sophisticated, not because it is visually busy.

## 16. Definition of UX MVP done

The AURORA UX MVP is complete when a new user can:

1. enter a workspace;
2. import useful source material;
3. ask a meaningful question;
4. understand the answer's epistemic status;
5. inspect the evidence behind it;
6. see when/why QUORUM was invoked;
7. inspect model disagreement without losing the synthesis;
8. traverse from answer → evidence → source → reasoning;
9. identify unresolved contradictions/gaps;
10. create or inspect a goal/task/decision;
11. return later and understand what changed;
12. export the cognitive state without understanding AURORA's database schema.

The UX should make the distinctive AURORA thesis obvious within the first few minutes: **this is not merely a chatbot; it is a persistent, inspectable cognitive workspace.**
