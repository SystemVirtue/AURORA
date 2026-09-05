# AURORA — Dawn for Transparent AI

> **A persistent, inspectable cognitive environment in which AI reasoning leaves an evidence trail.**

AURORA is not another chatbot wrapper. It is a cognitive substrate in which conversations, documents, claims, evidence, reasoning, beliefs, decisions, goals, tasks and memory remain connected, temporal and inspectable.

## What AURORA is trying to prove

The first product is **AURORA — a Transparent Cognitive Workspace**.

The core cognitive loop is:

**ASK → INVESTIGATE → WARRANT → REASON / QUORUM → EXPLAIN → REMEMBER**

The MVP proves that this loop can operate over a durable cognitive substrate rather than over transient chat history.

AURORA deliberately separates what a user or model **said**, what a source **supports**, what AURORA currently **believes**, what is represented as a **fact**, what remains **unknown or contested**, what reasoning produced an answer, and what decisions/actions depend on the resulting state.

A model contribution is **not automatically a fact**. Historical imported model output remains attributed historical context. Candidate claims are initially unverified. Disagreement is retained rather than silently averaged away.

## Current MVP status — 6 September 2026

**Overall engineering estimate: ~97% toward the defined MVP.**

This is a weighted engineering estimate, not a feature-count percentage. The complete deterministic MVP acceptance lifecycle now passes CI, including authenticated workspace creation, evidence ingestion/retrieval, contradiction-driven QUORUM, provenance, belief revision, goals/tasks/decisions, conversation import, export, destruction, restore and post-restore reasoning.

### CI proof

**AURORA CI #179 — run `33978787677` — commit `6c73b0c39041aaec87e5c0fee48051de53c7aa99` — PASS.**

All three jobs passed:

- **Python:** Ruff + full pytest suite.
- **Web:** JavaScript syntax, HTML linkage and authentication state fields.
- **Supabase:** local Supabase startup, migration reset, reincarnation/belief-revision proof, authenticated API QUORUM + continuity/reindex proof, full MVP acceptance, and deterministic QUORUM benchmark.

The Supabase job explicitly reports:

```text
AURORA reincarnation + belief-revision proof: PASS
API QUORUM + authenticated continuity + reindex/ask: PASS
AURORA MVP ACCEPTANCE: PASS
```

The deterministic benchmark currently reports 5 cases, aggregate evidence coverage **0.80 → 1.00**, unsupported rate **0.20 → 0.00**, disagreement preservation **1.00**, and quality delta **0.40**. These are evaluation results for the current benchmark, not a scientific claim that QUORUM is universally superior.

> **Important:** CI proves the repository against a fresh local Supabase environment. It does **not** by itself prove that the dedicated remote AURORA Supabase project has the latest schema or that a production runtime has been deployed and configured.

## Architecture

```text
USER / CLIENT
      │
      ▼
AURORA WEB UI
      │
      ▼
AURORA FASTAPI
      │
      ├── AUTH / WORKSPACE AUTHORIZATION
      │
      ├── INGESTION ──► SOURCES / DOCUMENTS / CONVERSATIONS
      │                         │
      │                         ▼
      └──────────────► EVENTS ─► CLAIMS ─► EVIDENCE
                                      │
                                      ▼
                              BELIEFS / MEMORY
                                      │
                                      ▼
                              HYBRID RETRIEVAL
                                      │
                                      ▼
                              REASONING GATEWAY
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                    SINGLE MODEL              QUORUM
                          │                       │
                          └───────────┬───────────┘
                                      ▼
                               ANSWER / DECISION
                                      │
                                      ▼
                              NEW COGNITIVE EVENTS
                                      │
                                      ▼
                              PORTABLE STATE
```

Supabase/PostgreSQL is the durable cognitive substrate. pgvector is used for derived embeddings/retrieval. A future NATS/event-distribution layer may distribute events, but it must not become a competing source of truth; an outbox pattern is preferred when asynchronous distribution is introduced.

## Canonical provenance

```text
SOURCE → EVENT → CLAIM → EVIDENCE → BELIEF/FACT → DECISION → ACTION
```

The design supports inspection in both directions:

> What evidence caused this conclusion?

and:

> What decisions or beliefs depend on this source?

## Five canonical primitives

1. **Identity** — who/what owns and produces cognition.
2. **Events** — durable history of meaningful state transitions.
3. **Claims** — explicit assertions, including unverified model assertions.
4. **Evidence** — first-class support, contradiction and qualification.
5. **Cognition** — beliefs, facts, memories, goals, tasks, decisions and reasoning.

Higher-order capabilities should use these primitives rather than create shadow state.

## Repository structure

```text
AURORA/
├── aurora/
│   ├── core.py                  # configuration, DB/core primitives
│   ├── gateway.py               # provider-neutral reasoning/embedding gateway
│   ├── cognition.py             # sessions, documents, chunks, retrieval
│   ├── claims.py                # candidate claim extraction/persistence
│   ├── quorum.py                # deliberation policy/comparison/synthesis prompt
│   ├── continuity.py             # authoritative export/manifest/checksums
│   ├── continuity_restore.py    # dependency-aware restore/rebinding
│   ├── importers.py             # ChatGPT/Claude/Gemini/generic normalization
│   └── evaluation.py            # deterministic QUORUM evaluation
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── action_routes.py
│   │   ├── revision_routes.py
│   │   ├── provenance_routes.py
│   │   ├── continuity_routes.py
│   │   └── import_routes.py
│   └── web/
│       ├── index.html           # canonical MVP workspace
│       └── app.js
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── scripts/
│   ├── dev-up.sh
│   ├── deploy-remote.sh
│   ├── restore-state.py
│   ├── test-reincarnation.py
│   ├── test-api-quorum.py
│   ├── test-mvp-acceptance.py
│   └── benchmark-quorum.py
├── tests/
├── docs/
│   ├── architecture/
│   ├── prompts/
│   ├── IMPLEMENTATION_STATUS.md
│   └── PITCH_60_SECOND.md
├── archive/predecessor/
└── setup_&_deployment MG and hopeful_guide.md
```

## MVP capabilities actually implemented

### Identity, tenancy and security boundary

- Supabase Auth-compatible JWT validation.
- JWT `sub` maps to the authenticated user identity.
- Explicit workspace membership checks at the API boundary.
- Workspace-scoped cognitive data.
- Supabase/Postgres RLS policies on the cognitive schema.
- Provider secrets remain server-side; the browser should never receive provider API keys or service-role credentials.

This is **MVP/development security**, not a claim of enterprise production hardening. Production deployment still requires correct secret management, HTTPS, origin policy, logging, rate limits and operational controls.

### Documents and evidence

`POST /v1/documents` creates source/document state, deterministically chunks content, records an ingestion event and creates conservative candidate claims. Candidate claims remain `unverified` until reviewed.

Evidence is first-class and is bound to current document chunks after continuity restore. Embeddings are derived and rebuildable rather than authoritative.

### Retrieval and reasoning

`POST /v1/ask` authenticates the user, verifies workspace/session access, persists the user message, retrieves lexical and optional semantic context, identifies relevant contradiction state, creates an explicit reasoning warrant where appropriate, invokes the provider-neutral gateway, persists reasoning runs/contributions/events, and returns answer, evidence, epistemic status and trace information.

If useful evidence is absent, AURORA can explicitly represent a `missing_evidence` epistemic gap rather than fabricate support.

### Selective QUORUM

QUORUM is a subsystem, not a competing product identity.

Current policy can escalate for explicit QUORUM mode, deep reasoning mode, relevant workspace contradiction, or missing evidence. The gateway runs independent contributors in parallel, retains failures as telemetry, compares contributions and performs a separate synthesis. Successful contributors and the synthesizer are persisted separately, preserving attribution, evidence IDs, latency and disagreement.

The current collective-gain metric is diagnostic. It is **not** a scientific proof of collective intelligence.

### Provenance

`GET /v1/provenance/claims/{claim_id}` exposes claim-level provenance through evidence, source/event, reasoning run, model contribution and QUORUM synthesis relationships.

### Belief revision

Claims support authenticated review into `unverified`, `supported`, `contested`, `rejected` and `superseded`. Revision is temporal: old belief versions close and new versions become current. Review events are recorded.

### Goals, tasks and decisions

Goals, tasks and decisions are part of the cognitive substrate rather than UI-only state. Tasks are included in continuity manifest version 3 and survive export/restore.

### Conversation import

The import layer supports normalized ingestion of ChatGPT, Claude, Gemini and generic conversation JSON. Historical model text remains historical attributed context and is **not automatically promoted to fact**.

### Machine reincarnation

AURORA's continuity invariant is:

> **No essential cognitive state may be irreversibly coupled to the lifetime of a particular runtime, server, model provider, orchestration framework or UI.**

Authoritative state is exported separately from derived state. The target recovery test is:

```text
Machine A
   ↓ export
portable state + checksums
   ↓
fresh database
   ↓ restore + rebuild derived chunks
   ↓ verify provenance/belief/action state
   ↓ ask again
Machine B
```

Embeddings and document chunks are derived/rebuildable. Authentication identities remain external dependencies; AURORA preserves references but does not export credentials or clone `auth.users`.

## API surface

Core endpoints currently include:

```text
GET  /health
GET  /health/db
POST /v1/sessions
POST /v1/documents
POST /v1/ask
POST /v1/reindex/embeddings
GET  /v1/claims/contradictions
POST /v1/claims/{claim_id}/review
GET  /v1/provenance/claims/{claim_id}
GET  /v1/workspaces
POST /v1/workspaces
GET  /v1/goals
POST /v1/goals
PATCH /v1/goals/{goal_id}
GET  /v1/tasks
POST /v1/tasks
PATCH /v1/tasks/{task_id}
POST /v1/decisions
GET  /v1/decisions
POST /v1/conversations/import
GET  /v1/continuity/export
POST /v1/continuity/restore
```

## Local setup

Requirements:

- Python 3.11+;
- Node.js 20+;
- Docker Desktop or compatible Docker runtime;
- an LLM provider key for real provider-backed reasoning.

The repository pins the Supabase CLI to **2.116.0**.

```bash
git clone https://github.com/SystemVirtue/AURORA.git
cd AURORA
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
npx supabase start
npx supabase db reset
```

Configure `.env` for local reasoning, for example:

```text
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
OPENROUTER_API_KEY=...
AURORA_DEFAULT_MODEL=...
```

Never commit `.env` or provider secrets.

Run the test suite:

```bash
pytest
ruff check .
```

Run the API:

```bash
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

Or use:

```bash
bash scripts/dev-up.sh
```

The canonical web assets are under `apps/web/`.

## Remote Supabase deployment

The repository does not hard-code a production project reference.

```bash
npx supabase login
bash scripts/deploy-remote.sh <SUPABASE_PROJECT_REF>
```

The script links the selected project, previews pending migrations and applies the migration set. Use a dedicated staging/development project before production.

**Remote schema status must be independently verified before declaring deployment complete.** Local CI migration success is not evidence that the remote project has been migrated.

## Render deployment

A `render.yaml` blueprint is included for the FastAPI container. It expects:

```text
DATABASE_URL
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_JWT_SECRET
AURORA_CORS_ORIGINS
OPENROUTER_API_KEY
OPENAI_API_KEY
AURORA_DEFAULT_MODEL
AURORA_EMBEDDING_MODEL
AURORA_REASONING_MODE
AURORA_QUORUM_MODELS
```

The health check is `/health`; the container listens on port `8000`.

The detailed operational procedure is maintained in **`setup_&_deployment MG and hopeful_guide.md`**. That guide separates local proof, remote database deployment, API deployment, provider-backed validation and production hardening.

## Environment and provider policy

See `.env.example` for the canonical environment list.

- **OpenRouter:** recommended primary MVP gateway.
- **OpenAI:** supported provider/fallback route.
- **Anthropic/Gemini/Ollama:** future/provider-extension direction; do not treat them as fully validated MVP deployments without runtime proof.
- **Browser:** never store provider API keys.

Embedding default is `text-embedding-3-small`. Embeddings are derived state and are rebuilt after continuity restore.

## Testing and verification

The full CI-equivalent local proof is:

```bash
npx supabase start
npx supabase db reset
python scripts/test-reincarnation.py
PYTHONPATH=. python scripts/test-api-quorum.py
PYTHONPATH=. python scripts/test-mvp-acceptance.py
PYTHONPATH=. python scripts/benchmark-quorum.py
```

The MVP acceptance contract is:

**identity → workspace → evidence → retrieval → contradiction/QUORUM → provenance → belief revision → goal/task/decision → conversation import → export → destroy → restore → post-restore ask**

The acceptance test monkeypatches the gateway only to make CI deterministic. A real-provider acceptance gate remains necessary after deployment.

## CI

`.github/workflows/ci.yml` validates:

1. Python quality/tests.
2. Canonical web assets.
3. A live local Supabase stack with migrations and cognitive lifecycle tests.

A green CI run is the minimum merge gate. It is not the same thing as production deployment.

## Continuity manifest

The current continuity format is **manifest version 3** because goals, tasks and decisions are authoritative state. Embeddings remain derived.

The exporter uses deterministic ordering and SHA-256 checksums. Restore is dependency-aware and explicitly maps authenticated users rather than cloning authentication credentials.

## Development lineage

AURORA is the clean implementation successor to `SystemVirtue/Supabase_Agentic_Assistant`. The predecessor is retained as an architectural R&D/archaeological layer and was not copied wholesale.

The separate Lovable project is not the canonical backend or cognitive database. The canonical MVP web assets live in this repository under `apps/web/`.

## Architecture documents and prompts

- `docs/architecture/AURORA_MVP_ARCHITECTURE.md` — architecture contract.
- `docs/architecture/ARCHITECTURE_PRINCIPLES.md` — invariants.
- `docs/IMPLEMENTATION_STATUS.md` — current implementation assessment.
- `docs/PITCH_60_SECOND.md` — executive pitch.
- `docs/prompts/AURORA_AGENT_MASTER_PROMPT.md` — current implementation master prompt.
- `docs/prompts/DEVELOPER_AGENT_MASTER_PROMPT_LEGACY.md` — predecessor-era prompt, historical only.
- `archive/predecessor/README.md` — lineage and archaeology.
- `setup_&_deployment MG and hopeful_guide.md` — setup, deployment, recovery and troubleshooting guide.

## Immediate post-MVP gates

1. Verify and migrate the dedicated remote Supabase project.
2. Deploy the FastAPI runtime.
3. Configure production auth/origin/provider secrets.
4. Run a real provider-backed acceptance test, including evidence retrieval and QUORUM.
5. Browser-smoke-test the canonical workspace.
6. Record the exact deployed commit and schema migration state.
7. Freeze the MVP contract.

## Later roadmap

Stronger retrieval/ranking, richer provenance dependency graphs, calibrated confidence, provider diversity, local-model routing, encrypted continuity transfer, UNBOX, distributed event transport, controlled agent swarms and controlled self-improvement are post-MVP directions.

## Definition of done

AURORA is MVP-complete when it can take real conversations and documents through:

**Ask → Investigate → Warrant → Reason → Explain → Remember**

while preserving evidence, provenance, uncertainty and cognitive history, and while surviving export/import into a fresh deployment.

The deterministic cognitive/data lifecycle now passes CI. The remaining gate is **real deployment and provider-backed operational validation**, followed by a controlled MVP freeze.

## Status discipline

> **Do not represent an architectural intention as an implemented capability.**

> **Do not represent a green local/CI test as proof of a remote production deployment.**

Every migration must pass `supabase db reset` locally/CI before remote deployment. Remote changes should use migration files and `supabase db push`; direct schema edits create drift.
