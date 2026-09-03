# AURORA ↔ Lovable Integration Contract

## Purpose

Lovable is the hosted presentation layer for AURORA. The `SystemVirtue/AURORA` repository remains the canonical implementation of the cognitive substrate and API.

Lovable must **not** recreate the AURORA reasoning engine, QUORUM orchestration, provenance store, or authoritative cognitive database.

## Runtime topology

```text
Browser
  │
  ▼
Lovable-hosted AURORA UI
  │ HTTPS + Supabase Bearer JWT
  ▼
AURORA FastAPI API
  ├── Supabase/PostgreSQL + pgvector
  └── Reasoning Gateway
       └── OpenRouter (MVP primary)
            ├── contributor A
            ├── contributor B
            └── contributor C
```

## Frontend configuration

The UI should expose only the following non-secret configuration:

- `VITE_AURORA_API_URL` — public HTTPS origin of the AURORA API.
- Supabase project URL / publishable key — only if the chosen deployment uses Supabase Auth directly from the browser.

Never put any of these in browser code:

- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`
- PostgreSQL service-role credentials

## API contract

### Authentication

Send:

```http
Authorization: Bearer <Supabase access token>
```

AURORA validates the JWT and separately checks workspace membership server-side.

### Health

`GET /health` is intentionally unauthenticated and is suitable for deployment probes.

`GET /health/db` checks database reachability and should not be exposed as a detailed public diagnostic endpoint in a hardened production deployment.

### Sessions

`POST /v1/sessions`

```json
{
  "workspace_id": "uuid",
  "title": "optional title"
}
```

Returns:

```json
{"session_id":"uuid"}
```

### Document ingestion

`POST /v1/documents`

```json
{
  "workspace_id": "uuid",
  "name": "document.txt",
  "content": "text...",
  "mime_type": "text/plain"
}
```

The response includes document/source IDs, chunk count, and candidate claim count. Candidate claims remain explicitly unverified until reviewed.

### Ask / reasoning

`POST /v1/ask`

```json
{
  "workspace_id": "uuid",
  "session_id": "uuid",
  "question": "What does the evidence show?",
  "model": "openrouter/<model>",
  "mode": "balanced"
}
```

`session_id` and `model` are optional. Supported MVP reasoning modes are:

- `fast`
- `balanced`
- `deep`
- `quorum`

The response can contain:

- `answer`
- `evidence`
- `evidence_ids`
- `model`
- `provider`
- `latency_ms`
- `trace`
- `quorum`

When QUORUM is invoked, the UI should visibly distinguish:

1. warrant for deliberation;
2. independent contributor responses;
3. failed contributors, if any;
4. evidence coverage;
5. agreement/disagreement diagnostics;
6. collective-gain diagnostic;
7. synthesis model/provider;
8. final synthesis.

The UI must not represent agreement as proof of truth.

### Contradictions

`GET /v1/claims/contradictions?workspace_id=<uuid>`

Use this to populate a contradiction/claim inspection view.

### Claim provenance

`GET /v1/provenance/claims/{claim_id}?workspace_id=<uuid>`

The response is a graph of claim → evidence → source/event and reasoning-run/model-contribution relationships. Render the graph as an inspectable evidence trail rather than as a generic social/knowledge graph.

### Claim review

`POST /v1/claims/{claim_id}/review`

The review UI should allow explicit status transitions using the API's supported statuses:

- `unverified`
- `supported`
- `contested`
- `rejected`
- `superseded`

A reviewer rationale should be captured when a human makes a material epistemic decision.

### Continuity

`GET /v1/continuity/export?workspace_id=<uuid>`

`POST /v1/continuity/restore`

Continuity is an authenticated cognitive-state operation. The UI should explain that:

- authoritative state is exported;
- credentials/auth identities are not exported;
- embeddings are derived and may need rebuilding;
- restore requires an explicit identity mapping;
- the target authenticated user must be represented in that mapping.

Do not describe JSON-over-HTTP continuity as the final high-volume production transport; it is the MVP integration surface.

## CORS

For a separately hosted Lovable origin, configure the AURORA API runtime with:

```text
AURORA_CORS_ORIGINS=https://<actual-lovable-origin>
```

Multiple exact origins may be comma-separated. Do not use `*` for authenticated browser traffic.

The exact Lovable origin should be added only after the final published domain is known.

## Product boundary

### In Lovable

- authentication screens;
- workspace/session navigation;
- chat/question composer;
- evidence cards;
- QUORUM deliberation visualization;
- contradiction view;
- provenance graph visualization;
- claim review workflow;
- document upload/import UX;
- continuity export/restore UX;
- responsive/mobile presentation;
- user-friendly error and loading states.

### In AURORA

- authentication validation;
- tenant/workspace authorization;
- cognitive persistence;
- retrieval;
- claims/evidence;
- belief revision;
- reasoning gateway;
- QUORUM policy/orchestration;
- provenance;
- continuity serialization/restoration;
- model/provider credentials;
- authoritative audit events.

## MVP acceptance test

A hosted Lovable build is considered integrated only when this path succeeds against a real deployed API:

```text
Sign in
  → select workspace
  → ingest document
  → ask question
  → retrieve evidence
  → receive answer
  → inspect trace
  → trigger/observe QUORUM when warranted
  → inspect contributor + synthesis provenance
  → inspect contradiction
  → review claim
  → export workspace
  → restore workspace
  → rebuild derived embeddings
  → ask again
```

This is the browser-facing end-to-end MVP proof.