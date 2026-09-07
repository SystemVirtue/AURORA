# AURORA UX-MVP Implementation Record

**Date:** 2026-09-08

## Scope delivered

The canonical `apps/web` client now has a thin UX layer over the existing working API client rather than a second application or framework.

### UX-MVP A — Application shell

- persistent AURORA navigation rail;
- workspace/context header;
- global Ask entry point;
- responsive navigation behaviour;
- dedicated views for Home, Think, Knowledge, Provenance, Action, Data IO and System;
- hash-based view navigation so the current workspace view is addressable.

### UX-MVP B — Home

Home is a summary layer rather than a second data store. It reads the already-rendered cognitive outputs and exposes:

- latest reasoning result;
- current epistemic status;
- retrieved evidence count;
- contradiction status;
- recommended next action.

No synthetic cognitive facts are created by the UX layer.

### UX-MVP C — Think

The existing functional reasoning controls are now grouped into a deliberate inspection sequence:

**question / investigation → answer → epistemic status + trace → QUORUM → retrieved evidence**

The existing model-access layer remains intact, including explicit provider/model selection and the OpenRouter-free / Puter pathways.

### Knowledge / Provenance / Action / Data IO

The existing working surfaces are now separated into navigable cognitive experiences:

- **Knowledge:** claims, contradiction detection and belief revision;
- **Provenance:** the existing claim provenance inspector, preserving claim → evidence → source/event → reasoning relationships;
- **Action:** goals, tasks and decisions;
- **Data IO:** conversation import and continuity export/restore validation;
- **System:** authentication and workspace controls.

This is an information-architecture refactor, not a backend rewrite.

## Design principles enforced

1. Summary before detail.
2. Inspection remains available one layer deeper.
3. Model agreement is not presented as truth.
4. Epistemic status remains explicit.
5. Existing API bindings and cognitive persistence are preserved.
6. The UX layer does not invent backend state.
7. AURORA is presented as a cognitive instrument/workspace rather than generic AI SaaS.
8. Responsive behaviour is included without introducing a frontend framework.

## Validation added

The canonical CI web job now checks `apps/web/ux.js` with Node syntax validation and verifies that `index.html` references the UX layer.

Browser-level interaction testing is **not yet claimed**. The next validation gate is a real browser smoke test against the deployed canonical API/Supabase environment.

## Files

- `apps/web/index.html` — mounts the UX layer;
- `apps/web/ux.js` — shell, navigation, Home summary and view composition;
- `apps/web/app.js` — existing cognitive API client remains authoritative for current operations;
- `apps/web/model_access.js` — existing explicit model/provider access layer remains authoritative for model execution UI.

## Deliberately deferred

This pass does not attempt to solve visual provenance graphs, global semantic search, a complete source/document explorer, advanced responsive layouts, accessibility certification, browser E2E automation, or a Figma-to-code pipeline. Those are subsequent increments after the information architecture has been exercised against real use.
