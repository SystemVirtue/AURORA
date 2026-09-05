# AURORA — Setup & Deployment Master Guide

**Filename:** `setup_&_deployment MG and hopeful_guide.md`  
**Project:** AURORA — Dawn for Transparent AI  
**Repository:** `SystemVirtue/AURORA`  
**Guide date:** 6 September 2026  
**Current MVP estimate:** ~97%  
**Latest CI proof:** AURORA CI #179 / run `33978787677` / commit `6c73b0c39041aaec87e5c0fee48051de53c7aa99`

---

## 0. Purpose of this guide

This is the operational master guide for taking a clean checkout of AURORA from **zero → local development → deterministic MVP verification → remote Supabase → API deployment → real provider validation → recovery/reincarnation**.

It is deliberately explicit about what is proven and what is not.

AURORA has now passed the complete deterministic cognitive/data lifecycle in GitHub Actions. That means the repository and its local Supabase migration set are coherent enough to prove the MVP substrate.

It does **not** mean that the production deployment is already complete.

The deployment sequence is therefore:

```text
SOURCE
  ↓
GitHub canonical repository
  ↓
Local environment
  ↓
Local Supabase + migrations
  ↓
Automated tests / acceptance proof
  ↓
Remote Supabase schema
  ↓
FastAPI runtime
  ↓
Authentication + CORS + secrets
  ↓
Real provider-backed reasoning
  ↓
Browser smoke test
  ↓
MVP freeze
```

Never skip a layer merely because the previous layer passed.

---

# 1. What is canonical?

## 1.1 Canonical backend/repository

The canonical project is:

```text
SystemVirtue/AURORA
```

The architecture is:

```text
AURORA/
├── aurora/                 # cognitive/core Python implementation
├── apps/api/               # FastAPI API
├── apps/web/              # canonical MVP browser workspace
├── supabase/              # schema, migrations, local config
├── scripts/               # developer, deployment and proof scripts
├── tests/                 # automated tests
├── docs/                  # architecture, prompts and status
└── archive/predecessor/   # archaeological predecessor material
```

## 1.2 Canonical UI

The canonical MVP UI is:

```text
apps/web/index.html
apps/web/app.js
```

The separate Lovable project is **not** the canonical cognitive backend, database or source of truth.

Do not create a second Supabase project or database for the Lovable UI.

## 1.3 Canonical database

Supabase/PostgreSQL is the durable cognitive substrate.

The schema is migration-driven:

```text
supabase/migrations/
  202609030001_initial_cognitive_substrate.sql
  202609030002_retrieval_and_continuity.sql
  202609030003_claim_provenance.sql
  202609030004_belief_revision.sql
  202609030005_belief_revision_reviewer_membership.sql
  202609060001_tasks_and_cognitive_actions.sql
```

The current continuity manifest is **version 3**.

## 1.4 Predecessor

`SystemVirtue/Supabase_Agentic_Assistant` is the historical architectural/R&D predecessor.

It must not be treated as the current implementation and should not be merged back wholesale.

---

# 2. Current implementation state

As of 6 September 2026:

**Overall: approximately 97% toward the defined MVP.**

The important distinction is that the core cognitive lifecycle is now executable and tested.

Implemented MVP substrate includes:

- authenticated identity;
- workspace tenancy;
- RLS-backed cognitive data;
- sessions and messages;
- document ingestion;
- deterministic document chunking;
- candidate claims;
- first-class evidence;
- lexical retrieval;
- optional semantic retrieval;
- hybrid retrieval;
- reasoning runs;
- provider-neutral reasoning gateway;
- explicit epistemic warrants/gaps;
- selective QUORUM;
- persisted model contributions;
- QUORUM synthesis;
- contradiction detection;
- claim review and belief revision;
- provenance inspection;
- goals;
- tasks;
- decisions;
- ChatGPT/Claude/Gemini/generic conversation import;
- deterministic continuity export;
- dependency-aware restore;
- derived chunk rebuild;
- reincarnation proof;
- canonical browser workspace;
- deterministic MVP acceptance;
- deterministic QUORUM evaluation.

The principal remaining MVP gate is operational: **remote deployment + real provider-backed validation + final browser smoke test + freeze**.

---

# 3. Latest CI proof

The latest canonical CI run is:

```text
AURORA CI #179
Run: 33978787677
Commit: 6c73b0c39041aaec87e5c0fee48051de53c7aa99
Result: PASS
```

Jobs:

```text
Python     PASS
Web        PASS
Supabase   PASS
```

The Supabase job proved:

```text
Supabase startup                         PASS
Migration reset                          PASS
Reincarnation + belief revision          PASS
API QUORUM + authenticated continuity   PASS
Full MVP acceptance                      PASS
QUORUM benchmark                         PASS
```

The benchmark currently reports:

```text
cases:                         5
evidence coverage:             0.80 → 1.00
unsupported rate:              0.20 → 0.00
disagreement preservation:     1.00
quality delta:                 0.40
```

These figures describe the deterministic benchmark suite. They are not a scientific claim that QUORUM always outperforms a single model.

---

# 4. Prerequisites

Install:

- Git;
- Python 3.11+;
- Node.js 20+;
- npm;
- Docker Desktop or compatible Docker Engine;
- a GitHub account with repository access;
- a Supabase account/project for remote deployment;
- a Render account if deploying the API through Render;
- an LLM provider account/key for real reasoning.

Recommended development environment:

```text
Python 3.12
Node 20+
Docker current stable
Supabase CLI 2.116.0
```

The repository pins the Supabase CLI package to 2.116.0.

---

# 5. Clean local installation

## 5.1 Clone

```bash
git clone https://github.com/SystemVirtue/AURORA.git
cd AURORA
```

Confirm you are on the canonical branch:

```bash
git branch --show-current
git log -1 --oneline
```

The deployed/reviewed MVP baseline should ultimately record the exact commit used.

## 5.2 Node dependencies

```bash
npm install
```

## 5.3 Python environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 5.4 Environment file

```bash
cp .env.example .env
```

Never commit `.env`.

Never put provider keys into browser JavaScript.

---

# 6. Local Supabase

AURORA uses Supabase locally for PostgreSQL, Auth-compatible infrastructure and pgvector-backed database functionality.

Start it:

```bash
npx supabase start
```

Reset/apply all migrations:

```bash
npx supabase db reset
```

A successful reset must apply every AURORA migration in sequence.

Expected migration sequence:

```text
001 initial cognitive substrate
002 retrieval + continuity
003 claim provenance
004 belief revision
005 reviewer membership
006 tasks + cognitive actions
```

Do not manually edit the local database as a substitute for migrations.

If you make a schema change, create a migration.

---

# 7. Local environment configuration

The minimum local database configuration is normally:

```text
AURORA_ENV=development
AURORA_HOST=127.0.0.1
AURORA_PORT=8000
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

For real provider-backed reasoning, configure:

```text
OPENROUTER_API_KEY=<server-side secret>
AURORA_DEFAULT_MODEL=<provider/model identifier>
```

Optional:

```text
AURORA_QUORUM_MODELS=model-a,model-b,model-c
AURORA_CORS_ORIGINS=<allowed browser origins>
```

Embedding default:

```text
AURORA_EMBEDDING_MODEL=text-embedding-3-small
```

Do not put secrets into:

- `README.md`;
- JavaScript;
- HTML;
- migration files;
- Git history;
- screenshots;
- issue comments.

If a real credential is accidentally committed, rotate it.

---

# 8. Start AURORA locally

The simplest path is:

```bash
bash scripts/dev-up.sh
```

This is the preferred developer shortcut.

For manual operation:

```bash
npx supabase start
npx supabase db reset
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

API:

```text
http://127.0.0.1:8000
```

Health:

```text
GET /health
```

Database health:

```text
GET /health/db
```

The browser assets are under:

```text
apps/web/
```

For local UI testing, serve them through the same development/API origin or another explicitly configured local web server.

---

# 9. Run the normal test suite

```bash
ruff check .
pytest -q
```

Both must pass before considering the local environment healthy.

---

# 10. Run the full MVP proof locally

This is the most important local verification sequence.

```bash
npx supabase start
npx supabase db reset
python scripts/test-reincarnation.py
PYTHONPATH=. python scripts/test-api-quorum.py
PYTHONPATH=. python scripts/test-mvp-acceptance.py
PYTHONPATH=. python scripts/benchmark-quorum.py
```

The complete acceptance lifecycle is:

```text
IDENTITY
   ↓
WORKSPACE
   ↓
EVIDENCE / DOCUMENT
   ↓
RETRIEVAL
   ↓
CONTRADICTION / QUORUM
   ↓
PROVENANCE
   ↓
BELIEF REVISION
   ↓
GOAL / TASK / DECISION
   ↓
CONVERSATION IMPORT
   ↓
EXPORT
   ↓
DESTROY
   ↓
RESTORE
   ↓
POST-RESTORE ASK
```

A failure is an engineering defect or environmental problem to investigate. Do not simply mark the test as non-blocking.

---

# 11. Understand what the MVP actually proves

AURORA is not merely proving that an LLM can answer a question.

It is proving that the answer can exist inside a persistent cognitive substrate with:

```text
identity
history
evidence
claims
belief state
uncertainty
reasoning trace
model attribution
contradiction
actions
continuity
```

The key lifecycle is:

```text
ASK
 ↓
INVESTIGATE
 ↓
WARRANT
 ↓
REASON / QUORUM
 ↓
EXPLAIN
 ↓
REMEMBER
```

---

# 12. Authentication model

AURORA uses Supabase-compatible JWT authentication.

The API validates:

- JWT signature;
- expiration;
- subject (`sub`);
- workspace membership.

The authenticated JWT subject becomes the user identity used by the API.

Important:

**Authentication identity is external to AURORA continuity.**

The continuity system does not export passwords, refresh tokens or cloned `auth.users` credentials.

Restore therefore requires explicit mapping from exported cognitive user IDs to real authenticated users in the destination environment.

---

# 13. Workspace onboarding

The canonical API provides:

```text
GET  /v1/workspaces
POST /v1/workspaces
```

The browser workspace uses these endpoints for onboarding/discovery.

A user must have workspace membership before accessing workspace-scoped cognitive data.

Do not weaken this by adding blanket policies such as:

```sql
USING (true)
```

unless a future architecture explicitly requires it and the security consequences have been reviewed.

---

# 14. Document ingestion

Endpoint:

```text
POST /v1/documents
```

The ingestion path creates:

```text
source
  ↓
document
  ↓
document_chunks
  ↓
ingestion event
  ↓
candidate claims
  ↓
evidence
```

Candidate claims are conservative and initially:

```text
assertion_status = unverified
```

This is intentional.

Ingestion must not silently turn imported text into truth.

---

# 15. Asking AURORA a question

Endpoint:

```text
POST /v1/ask
```

Conceptual request:

```json
{
  "workspace_id": "<workspace UUID>",
  "question": "What do we currently know about AURORA?",
  "mode": "balanced"
}
```

The request path is approximately:

```text
JWT
 ↓
workspace authorization
 ↓
persist user message
 ↓
lexical retrieval
 ↓
optional semantic retrieval
 ↓
hybrid ranking
 ↓
contradiction check
 ↓
warrant determination
 ↓
reasoning gateway
 ↓
optional QUORUM
 ↓
persist reasoning/contributions/events
 ↓
answer + evidence + trace
```

---

# 16. Reasoning modes

Current conceptual modes include:

```text
fast
balanced
deep
quorum
```

Normal `balanced` reasoning should not automatically incur QUORUM cost when strong useful evidence exists and no special warrant is present.

QUORUM may be invoked when:

- explicitly requested;
- deep reasoning is selected;
- relevant workspace contradictions exist;
- evidence is missing.

The principle is:

> Use multiple independent reasoning paths when doing so is justified by the epistemic state, not merely because multiple models are available.

---

# 17. QUORUM configuration

Optional environment setting:

```text
AURORA_QUORUM_MODELS=model1,model2,model3
```

The current gateway caps contributors at three per deliberation.

The execution path is:

```text
QUESTION
 ↓
WARRANT
 ↓
parallel independent contributors
 ↓
comparison
 ↓
synthesis
 ↓
persist contributor records
 ↓
persist synthesis
 ↓
persist QUORUM event
 ↓
provenance/UI inspection
```

Contributor identity, model/provider, response, evidence IDs and latency are retained.

Failures should remain observable rather than being silently discarded.

The current benchmark's collective-gain metric is diagnostic only.

---

# 18. Provenance inspection

Endpoint:

```text
GET /v1/provenance/claims/{claim_id}?workspace_id=<workspace UUID>
```

The current provenance graph can connect:

```text
CLAIM
 ↓
EVIDENCE
 ↓
SOURCE / EVENT
 ↓
REASONING RUN
 ↓
MODEL CONTRIBUTION
 ↓
QUORUM SYNTHESIS
```

The purpose is not decorative tracing.

The intended question is:

> **Why should I believe this?**

and:

> **What caused this conclusion?**

---

# 19. Belief revision

Endpoint:

```text
POST /v1/claims/{claim_id}/review
```

Supported review states include:

```text
unverified
supported
contested
rejected
superseded
```

Revision is temporal.

The database records the transition rather than simply overwriting history.

A review should therefore be treated as a cognitive event, not a mutable UI flag.

---

# 20. Goals, tasks and decisions

The cognitive action substrate currently exposes:

```text
GET/POST/PATCH goals
GET/POST/PATCH tasks
GET/POST decisions
```

Tasks are authoritative state.

This matters because a task that exists only in the browser would disappear during machine reincarnation.

Current continuity manifest version 3 explicitly includes tasks.

---

# 21. Conversation import

Endpoint:

```text
POST /v1/conversations/import
```

Supported normalization targets:

```text
chatgpt
claude
gemini
generic
```

The import pipeline is designed as:

```text
RAW CONVERSATION
 ↓
SOURCE METADATA
 ↓
INTERACTION EVENTS
 ↓
ASSERTIONS / CLAIMS
 ↓
PROVENANCE
 ↓
EVIDENCE ASSESSMENT
 ↓
CANDIDATE MEMORY
 ↓
PROMOTION / REJECTION
```

Historical model output must remain attributed historical context.

Do not automatically promote it to fact.

---

# 22. Machine reincarnation

The defining continuity rule is:

> **No essential cognitive state may be irreversibly coupled to the lifetime of a particular runtime, server, model provider, orchestration framework or UI.**

AURORA separates:

```text
AUTHORITATIVE
─────────────
workspace state
sources
sessions
messages
events
claims
evidence
entities
relationships
beliefs
memories
goals
tasks
decisions
reasoning runs
model contributions
epistemic gaps

DERIVED
───────
document chunks
embeddings
indexes
```

Derived state can be rebuilt.

Authoritative state must survive.

---

# 23. Continuity export

API:

```text
GET /v1/continuity/export?workspace_id=<workspace UUID>
```

The continuity implementation also provides Python-level export functionality.

The export uses deterministic ordering and SHA-256 checksums.

The manifest is currently version 3.

A conceptual package looks like:

```text
aurora-export/
├── manifest.json
├── schema/
├── events/
├── conversations/
├── claims/
├── evidence/
├── entities/
├── relationships/
├── memories/
├── goals/
├── tasks/
├── decisions/
├── reasoning_runs/
├── contributions/
├── epistemic_gaps/
├── provenance/
├── documents/
├── embeddings/
└── checksums/
```

The actual exporter may serialize these structures differently; the important contract is authoritative-vs-derived separation and deterministic verification.

---

# 24. Continuity restore

API:

```text
POST /v1/continuity/restore
```

Restore is dependency-aware.

Important sequence:

```text
users/workspace mappings
 ↓
workspace/source/document state
 ↓
documents
 ↓
rebuild document chunks
 ↓
evidence rebinding
 ↓
claims / cognition / actions
 ↓
reasoning/contributions
 ↓
provenance verification
```

The current implementation deliberately does not restore old `document_chunk_id` values as authoritative because chunks are derived and may receive new IDs.

Instead, evidence is rebound to rebuilt chunks using its authoritative excerpt/document relationship.

Embeddings are rebuilt after restore.

---

# 25. CLI restore

The repository provides:

```bash
python scripts/restore-state.py --help
```

Use dry-run validation before a destructive or production restore.

The restore tool requires an explicit database connection and user mapping.

Do not use a production database for experiments.

---

# 26. Remote Supabase deployment

## 26.1 Principle

Remote schema is managed by migration files.

Do not use ad-hoc SQL editor changes for application schema unless the change is immediately represented by a migration and the drift is reconciled.

Preferred flow:

```text
migration file
 ↓
supabase db reset
 ↓
CI
 ↓
supabase db push
 ↓
remote verification
```

## 26.2 Login

```bash
npx supabase login
```

Use the Supabase CLI's authentication mechanism.

## 26.3 Link the intended project

```bash
npx supabase link --project-ref <SUPABASE_PROJECT_REF>
```

Confirm that the selected project is the intended **AURORA** project before pushing anything.

Do not assume the predecessor project is the target.

## 26.4 Preview migration state

Before applying migrations, inspect the pending changes.

Use the Supabase CLI migration/status facilities appropriate to the installed CLI version.

The goal is to establish:

```text
local migration history
        vs
remote migration history
```

If they disagree unexpectedly, stop and investigate migration drift.

## 26.5 Apply migrations

```bash
npx supabase db push
```

Or use the project helper:

```bash
bash scripts/deploy-remote.sh <SUPABASE_PROJECT_REF>
```

The helper is the preferred repository-level workflow because it keeps deployment aligned with the repository migration set.

---

# 27. Remote database verification

After pushing migrations, verify at minimum:

```text
workspace tables exist
RLS policies exist
claims exist
 evidence exists
goals exist
tasks exist
decisions exist
reasoning_runs exist
model_contributions exist
epistemic_gaps exist
revision function exists
provenance path exists
pgvector extension/indexes exist where expected
```

The crucial point:

**A green GitHub Actions run does not prove the remote Supabase project was migrated.**

The local CI environment is disposable.

Remote verification is a separate deployment gate.

---

# 28. AURORA remote Supabase project

A dedicated AURORA Supabase project exists and is the intended remote database target for this implementation.

Project details should be obtained from the operator's secure Supabase account/CLI configuration rather than copied into public source files.

Do not put:

- database passwords;
- service-role keys;
- JWT secrets;
- provider keys;

into this guide.

The repository's `.env.example` is the configuration contract; actual secrets belong in the deployment platform's secret store.

---

# 29. Render API deployment

The repository includes:

```text
render.yaml
Dockerfile
```

The Render blueprint describes a Docker web service named `aurora-api`.

Health check:

```text
/health
```

Container port:

```text
8000
```

## Required runtime environment

Configure through Render's secret/environment UI:

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

Not every variable needs a real value in every deployment, but every intentionally unused capability should be understood before leaving it blank.

For an OpenRouter-first deployment, the minimum reasoning set is normally:

```text
DATABASE_URL
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_JWT_SECRET
OPENROUTER_API_KEY
AURORA_DEFAULT_MODEL
AURORA_EMBEDDING_MODEL
AURORA_REASONING_MODE
AURORA_CORS_ORIGINS
```

## Important

`SUPABASE_JWT_SECRET` must match the JWT signing configuration used by the Supabase Auth project.

Do not confuse:

```text
publishable/anon key
```

with:

```text
JWT signing secret
```

They serve different purposes.

---

# 30. Database connection choice

For the deployed API, use the appropriate Supabase/Postgres connection for the deployment environment.

The preferred operational approach is generally the **Session Pooler** when a hosted runtime requires a stable IPv4-compatible PostgreSQL connection.

Do not casually use a direct IPv6-only database endpoint from a hosting provider that cannot reach it.

The runtime `DATABASE_URL` must be tested from the actual API deployment environment.

---

# 31. CORS

If the UI is served from a different origin, configure:

```text
AURORA_CORS_ORIGINS
```

Use exact origins.

Example conceptually:

```text
https://aurora.example.com
```

Do not use unrestricted production CORS such as:

```text
*
```

when authenticated browser credentials are involved.

For a same-origin deployment, leaving CORS empty is preferable if the application supports that topology.

---

# 32. Provider configuration

## 32.1 OpenRouter

OpenRouter is the recommended primary MVP provider boundary.

The API key belongs only on the server.

Configure:

```text
OPENROUTER_API_KEY=<secret>
AURORA_DEFAULT_MODEL=<OpenRouter model identifier>
```

## 32.2 OpenAI

OpenAI is supported as a provider/fallback route.

Do not configure an OpenAI key merely because the variable exists.

If OpenAI is required and a key does not already exist, follow the project's credential policy: use an existing approved key by default or explicitly create a new one through the appropriate secure account workflow.

Never paste provider secrets into this chat or into GitHub source files.

## 32.3 Other providers

Anthropic, Gemini and Ollama are architectural/provider-extension directions. They must not be described as production-validated merely because environment variables or routing placeholders exist.

---

# 33. First real provider-backed acceptance test

This test should happen **after** remote Supabase and API deployment are independently healthy.

Test sequence:

1. Create/sign in a real test user.
2. Create a test workspace.
3. Ingest a small known document.
4. Confirm candidate claim/evidence creation.
5. Ask a question directly supported by the document.
6. Confirm returned evidence references the document.
7. Ingest a deliberately contradictory document.
8. Ask the relevant question again.
9. Confirm contradiction detection.
10. Confirm QUORUM escalation where warranted.
11. Inspect the reasoning trace.
12. Inspect claim provenance.
13. Review a claim.
14. Create a goal/task/decision.
15. Import a historical conversation.
16. Export the workspace.
17. Validate the export/checksums.
18. Restore into a disposable destination workspace/database.
19. Reindex/rebuild derived state.
20. Ask the original question again.
21. Confirm evidence/provenance continuity.

This is the operational equivalent of the deterministic CI acceptance path.

---

# 34. Browser smoke test

The canonical browser workspace should be tested after the API is deployed.

Minimum browser checklist:

```text
[ ] Sign in
[ ] Sign out
[ ] Token persistence works
[ ] Workspace list works
[ ] Workspace creation works
[ ] Select workspace
[ ] Ingest document
[ ] Ask question
[ ] See answer
[ ] See evidence
[ ] See epistemic/warrant state
[ ] See reasoning trace
[ ] See QUORUM where triggered
[ ] Inspect contradiction
[ ] Inspect provenance
[ ] Review claim
[ ] Create goal
[ ] Create task
[ ] Create decision
[ ] Import conversation
[ ] Export continuity state
[ ] Restore validation
```

Do not call the browser UI complete merely because JavaScript syntax checks pass.

CI's web job currently verifies structural assets such as:

```text
app.js syntax
index.html presence
app.js linkage
token field
refreshToken field
```

Those checks are necessary but not equivalent to browser acceptance.

---

# 35. Production security checklist

Before exposing AURORA publicly:

```text
[ ] HTTPS enforced
[ ] production JWT secret configured
[ ] provider secrets stored only in secret manager
[ ] database credentials stored only in secret manager
[ ] CORS restricted to exact trusted origins
[ ] service-role credentials never sent to browser
[ ] database connection uses appropriate SSL/security settings
[ ] RLS verified on all exposed cognitive tables
[ ] API membership checks verified
[ ] rate limiting considered
[ ] request/body size limits considered
[ ] error messages do not expose secrets
[ ] logs do not contain provider keys/tokens
[ ] backup/recovery plan exists
[ ] continuity export handling is secured
[ ] exported cognitive data is treated as sensitive project data
```

AURORA's current MVP security posture should be described as **development/MVP-grade**, not enterprise-grade.

---

# 36. Migration discipline

Every schema change follows:

```text
1. Edit/create migration
2. supabase db reset
3. Run tests
4. Run CI
5. Inspect migration history
6. supabase db push to intended remote
7. Verify remote schema
```

Never:

```text
remote SQL edit
↓
forget migration
↓
continue development
```

That creates schema drift and eventually makes reincarnation unreliable.

---

# 37. Troubleshooting — local Supabase

## Docker cannot start

Check:

```bash
docker version
docker ps
```

Make sure Docker Desktop/Engine is running.

## Supabase CLI version mismatch

Check:

```bash
npx supabase --version
```

The repository expects:

```text
2.116.0
```

## Migration failure

Run:

```bash
npx supabase db reset
```

Read the first failing migration, not merely the final stack trace.

Then inspect migration ordering and dependencies.

Do not manually patch the local database to hide the migration defect.

---

# 38. Troubleshooting — API returns 503 for authenticated routes

The most common cause is missing or invalid:

```text
SUPABASE_JWT_SECRET
```

Check the API environment.

The API intentionally does not pretend authentication works if the JWT configuration is unavailable.

---

# 39. Troubleshooting — API cannot connect to database

Check:

```text
DATABASE_URL
```

Then verify the endpoint is reachable from the deployment environment.

For hosted deployments, consider Supabase Session Pooler rather than a direct IPv6-only endpoint.

Do not paste database passwords into support chats.

---

# 40. Troubleshooting — reasoning fails

Check:

```text
OPENROUTER_API_KEY
AURORA_DEFAULT_MODEL
provider availability
network egress
API logs
```

Remember that CI's deterministic tests monkeypatch the gateway where necessary.

Therefore:

```text
CI PASS
```

does not prove:

```text
real provider credentials + network + model availability
```

Those are a separate runtime gate.

---

# 41. Troubleshooting — QUORUM appears to use only one model

Check:

```text
AURORA_QUORUM_MODELS
```

If only one effective model is available, QUORUM may structurally behave like one contributor plus synthesis.

For a meaningful real-world QUORUM experiment, configure multiple independent model routes.

Do not claim model diversity unless the runtime logs prove it.

---

# 42. Troubleshooting — evidence disappears after restore

Check whether the restored document chunks were rebuilt.

This is expected architecture:

```text
document_chunk IDs are derived
```

Evidence must rebind to the rebuilt chunk using authoritative document/excerpt information.

The reincarnation test specifically verifies that restored evidence receives a valid rebuilt `document_chunk_id`.

Do not make old chunk UUIDs authoritative merely to make a test pass.

---

# 43. Troubleshooting — tasks disappear after restore

This should now be treated as a regression.

Tasks are authoritative state and are included in continuity manifest version 3.

Run:

```bash
python scripts/test-reincarnation.py
PYTHONPATH=. python scripts/test-mvp-acceptance.py
```

If tasks are missing, inspect:

```text
continuity authoritative tables
export manifest
restore ordering
```

---

# 44. Troubleshooting — remote schema differs from local

Stop deployment.

Compare:

```text
supabase/migrations/
```

with the remote migration history.

Do not blindly run destructive resets against production.

Determine whether the remote environment contains:

- missing migrations;
- manually-created tables;
- divergent functions;
- old predecessor schema;
- partially applied AURORA schema.

The correct answer is to reconcile migration history, not to improvise over it.

---

# 45. Troubleshooting — browser auth works but API rejects the token

Check that:

```text
browser Supabase project
        =
API SUPABASE_URL
        =
API SUPABASE_JWT_SECRET
        =
remote Supabase Auth project
```

The most common architectural error is accidentally using credentials from different Supabase projects.

AURORA must use one authoritative Auth/database project for a deployment.

---

# 46. Disaster recovery / machine reincarnation procedure

When moving AURORA to a new machine/server:

## Step 1 — install repository

```bash
git clone https://github.com/SystemVirtue/AURORA.git
cd AURORA
```

## Step 2 — install dependencies

```bash
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Step 3 — establish destination database

```bash
npx supabase start
npx supabase db reset
```

or configure the destination remote database.

## Step 4 — obtain portable export

Use the source environment's continuity export.

## Step 5 — validate checksums

Never restore a damaged or incomplete package.

## Step 6 — establish destination user mappings

Do not copy authentication credentials from the source.

Map cognitive user IDs to destination authenticated users.

## Step 7 — dry run restore

Use the restore CLI/API validation mode.

## Step 8 — restore

Execute dependency-aware restore.

## Step 9 — rebuild derived state

Rebuild document chunks and embeddings as required.

## Step 10 — verify

Check:

```text
claims
evidence
beliefs
memories
goals
tasks
decisions
reasoning runs
model contributions
epistemic gaps
provenance
```

## Step 11 — ask again

The final test is not whether the database contains rows.

It is:

> **Can AURORA continue where it left off?**

---

# 47. MVP freeze criteria

Do not freeze the MVP until all are true:

```text
[✓] repository CI green
[✓] Python suite green
[✓] web structural checks green
[✓] local migrations reset cleanly
[✓] reincarnation proof green
[✓] API QUORUM integration green
[✓] full deterministic MVP acceptance green
[✓] benchmark executes
[ ] remote Supabase migration independently verified
[ ] deployed API health independently verified
[ ] real provider-backed reasoning verified
[ ] real QUORUM verified
[ ] browser smoke test completed
[ ] exact deployed commit recorded
[ ] exact remote schema/migration state recorded
```

The first eight items are now demonstrated by the latest CI run.

The remaining items are deployment/operations gates.

---

# 48. What must NOT be claimed yet

Until the deployment gates are completed, do not say:

```text
“AURORA is live in production.”
“AURORA's remote schema is verified.”
“OpenRouter production reasoning is verified.”
“QUORUM is scientifically superior.”
“AURORA is enterprise secure.”
“Every provider is fully integrated.”
“Continuity is production-grade encrypted disaster recovery.”
```

The accurate statement is:

> **AURORA's deterministic cognitive MVP lifecycle is implemented and passing CI; remote deployment and real provider-backed operational validation remain the final gates.**

---

# 49. Recommended deployment order from here

Execute in this exact order:

```text
1. Confirm current GitHub main commit
        ↓
2. Confirm CI #179 PASS
        ↓
3. Verify intended AURORA Supabase project
        ↓
4. Link repository to intended Supabase project
        ↓
5. Inspect migration drift
        ↓
6. Push migrations
        ↓
7. Independently verify remote schema
        ↓
8. Deploy FastAPI container to Render
        ↓
9. Configure runtime secrets
        ↓
10. Verify /health
        ↓
11. Verify /health/db
        ↓
12. Verify authenticated workspace path
        ↓
13. Run real provider-backed question
        ↓
14. Run real evidence-backed question
        ↓
15. Trigger real contradiction/QUORUM
        ↓
16. Inspect provenance
        ↓
17. Exercise goals/tasks/decisions
        ↓
18. Import a real test conversation
        ↓
19. Export continuity state
        ↓
20. Restore into disposable destination
        ↓
21. Ask again
        ↓
22. Browser smoke test
        ↓
23. Record deployment commit/schema
        ↓
24. Freeze MVP
```

This is the preferred path.

---

# 50. Operational rule: evidence before optimism

AURORA's own architecture should govern how it is developed.

If something is not verified, mark it as:

```text
unverified
```

If a deployment has not been tested, mark it:

```text
not yet verified
```

If two sources disagree, retain the disagreement.

If evidence is missing, represent the epistemic gap.

The deployment process should follow exactly the same discipline as the product's cognitive model.

---

# 51. Useful commands — quick reference

## Install

```bash
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Local database

```bash
npx supabase start
npx supabase db reset
```

## Tests

```bash
ruff check .
pytest -q
```

## MVP proof

```bash
python scripts/test-reincarnation.py
PYTHONPATH=. python scripts/test-api-quorum.py
PYTHONPATH=. python scripts/test-mvp-acceptance.py
PYTHONPATH=. python scripts/benchmark-quorum.py
```

## API

```bash
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

## Developer shortcut

```bash
bash scripts/dev-up.sh
```

## Remote deployment

```bash
npx supabase login
bash scripts/deploy-remote.sh <SUPABASE_PROJECT_REF>
```

## Restore

```bash
python scripts/restore-state.py --help
```

---

# 52. Final architectural position

AURORA should remain a **cognitive substrate first**.

Do not let deployment work pull the project into becoming merely:

```text
chat UI
+ LLM API
+ vector database
```

The differentiating architecture is:

```text
IDENTITY
  +
EVENT HISTORY
  +
CLAIMS
  +
EVIDENCE
  +
TEMPORAL BELIEF
  +
REASONING TRACE
  +
MODEL ATTRIBUTION
  +
CONTRADICTION
  +
GOALS / TASKS / DECISIONS
  +
CONTINUITY
```

QUORUM is a reasoning subsystem inside that substrate.

The UI is an inspection surface over that substrate.

The database is its durable memory.

The reasoning gateway is replaceable infrastructure.

The model provider is not the identity of AURORA.

The machine is not the identity of AURORA.

The cognitive state is.

---

# 53. Final MVP definition

AURORA reaches MVP when a real user can:

```text
sign in
  ↓
create/select workspace
  ↓
add evidence
  ↓
ask a question
  ↓
retrieve evidence
  ↓
reason transparently
  ↓
see uncertainty / warrant
  ↓
trigger QUORUM when justified
  ↓
inspect provenance
  ↓
revise beliefs
  ↓
create goals/tasks/decisions
  ↓
import prior conversation history
  ↓
export cognitive state
  ↓
restore it elsewhere
  ↓
continue reasoning
```

The deterministic implementation of this lifecycle is now passing CI.

The remaining work is to prove the same lifecycle against the intended remote infrastructure and real model provider, then freeze the MVP baseline.

**Do not confuse the architecture with the deployment. Do not confuse CI with production. Do not confuse model output with knowledge.**

That distinction is central to AURORA itself.
