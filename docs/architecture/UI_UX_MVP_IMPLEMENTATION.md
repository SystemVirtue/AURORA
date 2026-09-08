# AURORA UX-MVP Implementation Record

**Date:** 2026-09-08

## Scope delivered

The canonical `apps/web` client has a thin UX layer over the existing working API client rather than a second application or framework.

### UX-MVP A — Application shell

- persistent AURORA navigation rail;
- workspace/context header;
- global Ask entry point;
- responsive navigation behaviour;
- dedicated views for Home, Think, Knowledge, Provenance, Action, Data IO and System;
- hash-based view navigation so the current workspace view is addressable.

### UX-MVP B — Home

Home is a summary layer rather than a second data store. It reads already-rendered cognitive outputs and exposes latest reasoning, epistemic status, retrieved evidence count, contradiction state and next action.

### UX-MVP C — Think

Existing functional reasoning controls are grouped into a deliberate inspection sequence:

**question / investigation → answer → epistemic status + trace → QUORUM → retrieved evidence**

Raw reasoning trace and deeper deliberation details are progressively disclosed rather than occupying the primary surface.

### UX-MVP D/E — Knowledge and Provenance foundation

The working claims/contradiction/belief-revision surface is now a dedicated Knowledge experience, while its existing claim provenance inspector is exposed through the Provenance experience. The UX explicitly preserves the distinction between an evidence-backed claim, an unresolved/contested claim and a model assertion.

This pass does **not** invent a semantic graph or pretend that a general knowledge browser exists where the backend does not yet expose one.

### Action / Data IO / System

- **Action:** goals, tasks and decisions;
- **Data IO:** conversation import and continuity export/restore validation;
- **System:** authentication, workspace and model-access controls.

## Design principles enforced

1. Summary before detail.
2. Inspection remains available one layer deeper.
3. Model agreement is not presented as truth.
4. Epistemic status remains explicit.
5. Existing API bindings and cognitive persistence are preserved.
6. The UX layer does not invent backend state.
7. AURORA is presented as a cognitive instrument/workspace rather than generic AI SaaS.
8. Responsive behaviour is included without introducing a frontend framework.

## Validation

CI checks the web JavaScript with Node syntax validation and verifies that the UX layer is mounted by `index.html`.

Browser-level interaction testing is not yet claimed. A real browser smoke test against the deployed canonical API/Supabase environment remains an MVP gate.

## Next engineering increment

The next substantive UX increment is a **real Knowledge API/explorer** backed by the existing claims/evidence/document/chunk substrate, followed by a richer Provenance inspector and consolidated Data IO centre. These should expose actual backend objects rather than duplicating or fabricating state in the browser.

After those surfaces, add browser smoke/E2E validation and validate the complete user path:

**workspace → ingest → ask → epistemic status → evidence → QUORUM → claim → provenance → review → action → return → export**

## Deliberately deferred

- global semantic search;
- full source/document explorer;
- visual provenance graph;
- advanced responsive layouts;
- accessibility certification;
- browser E2E automation;
- Figma-to-code pipeline;
- platform-scale orchestration.
