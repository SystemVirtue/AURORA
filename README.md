# AURORA — Dawn for Transparent AI

> **A persistent, inspectable cognitive environment in which AI reasoning leaves an evidence trail.**

AURORA is not intended to be another chatbot wrapper. It is a cognitive substrate in which conversations, documents, claims, evidence, reasoning, beliefs, decisions and memory remain connected, temporal and inspectable.

## What AURORA is trying to prove

The first product is **AURORA — A Transparent Cognitive Workspace**.

The core loop is:

**ASK → INVESTIGATE → REASON → EXPLAIN → REMEMBER**

A successful MVP should let a user ask a question, retrieve relevant prior knowledge, reason over it, see the evidence and uncertainty behind the answer, preserve the resulting cognitive history, and later continue from that state.

## Why it is different

Conventional LLM applications commonly blur several different things:

- a model saying something;
- a source supporting something;
- the system believing something;
- a fact being true in the represented world;
- an explanation being generated after the fact;
- conversation history being treated as memory.

AURORA keeps those concepts separate.

A model contribution is **not automatically a fact**. A conclusion should be traceable through evidence. Disagreement is retained rather than silently averaged away. Unknowns are represented as state. Time distinguishes when something was true from when AURORA learned it.

## Canonical provenance

```text
SOURCE → EVENT → CLAIM → EVIDENCE → BELIEF/FACT → DECISION → ACTION
```

The system should support both forward and reverse inspection:

> What caused this decision?

and:

> What decisions or beliefs depend on this source?

## Five primitives

AURORA's canonical substrate is built around five primitives:

1. **Identity** — who/what owns and produces cognition.
2. **Events** — durable history of meaningful state transitions.
3. **Claims** — explicit assertions, including unverified model assertions.
4. **Evidence** — first-class support, contradiction and qualification.
5. **Cognition** — beliefs, facts, memories, goals, decisions and reasoning.

Higher-order capabilities must use this substrate rather than creating shadow state.

## Architecture

```text
USER / CLIENT
      │
      ▼
AURORA API / UI
      │
      ├── INGESTION ──► SOURCES / DOCUMENTS / CONVERSATIONS
      │                         │
      │                         ▼
      └──────────────► EVENTS ─► CLAIMS ─► EVIDENCE
                                      │
                                      ▼
                              MEMORY / BELIEFS
                                      │
                                      ▼
                              RETRIEVAL / CONTEXT
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
                                EVALUATION
                                      │
                                      ▼
                              ANSWER / DECISION
                                      │
                                      ▼
                                NEW EVENTS
                                      │
                                      ▼
                              COGNITIVE HISTORY
```

PostgreSQL/Supabase is the durable substrate. A future NATS JetStream layer can distribute events, but it must not become a second competing source of truth. An outbox pattern is preferred when asynchronous distribution is introduced.

## Current implementation

The repository currently contains the first executable substrate:

- FastAPI API baseline;
- provider-neutral reasoning gateway with OpenAI-compatible routing;
- durable reasoning runs and model contributions;
- canonical event recording;
- portable state bundle utility;
- Supabase/Postgres schema with workspace RLS;
- temporal claims, beliefs and relationships;
- generic conversation normalization;
- lightweight QUORUM contribution comparison;
- deterministic local tests;
- local Supabase deployment scripts;
- remote migration deployment script;
- AURORA and legacy developer-agent master prompts.

This is intentionally a **real thin slice**, not a claim that every architectural capability is finished.

## Repository layout

```text
AURORA/
├── aurora/                         # Core Python primitives
│   ├── core.py
│   ├── gateway.py
│   ├── continuity.py
│   ├── importers.py
│   └── quorum.py
├── apps/
│   └── api/main.py                 # First API surface
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── tests/
├── scripts/
│   ├── dev-up.sh
│   └── deploy-remote.sh
├── docs/
│   ├── architecture/
│   ├── prompts/
│   └── PITCH_60_SECOND.md
└── archive/
    └── predecessor/
```

## Quick start — local

Requirements:

- Python 3.11+;
- Node.js 20+;
- Docker Desktop or another Docker-compatible runtime;
- a model-provider API key for actual reasoning.

The repository pins the Supabase CLI to **2.116.0**. Supabase's documented local workflow is `supabase start` followed by migration/seed verification with `supabase db reset`.

### 1. Clone and install

```bash
git clone https://github.com/SystemVirtue/AURORA.git
cd AURORA
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

### 2. Start local Supabase

```bash
npx supabase start
npx supabase db reset
```

Keep the local stack bound to your machine; it is a development environment, not a production service.

### 3. Configure a model

Edit `.env`:

```text
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
OPENROUTER_API_KEY=...
AURORA_DEFAULT_MODEL=...
```

Never commit `.env` or provider secrets.

### 4. Run tests

```bash
pytest
```

### 5. Run the API

```bash
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
GET /health
```

Reasoning endpoint:

```text
POST /v1/ask
```

Example payload:

```json
{
  "workspace_id": "00000000-0000-0000-0000-000000000001",
  "question": "What do we currently know about AURORA?",
  "mode": "balanced"
}
```

## One-command developer launcher

```bash
bash scripts/dev-up.sh
```

This starts Supabase, resets the local database, sets the standard local database URL when needed, and starts the API.

## Remote Supabase deployment

The repository intentionally does **not** hard-code a production project reference.

```bash
npx supabase login
bash scripts/deploy-remote.sh <SUPABASE_PROJECT_REF>
```

The script links the selected project, previews pending migrations, then applies them. Use a dedicated development/staging project for initial testing.

## Database design

The first migration deliberately addresses defects identified in the predecessor:

- explicit workspace tenancy;
- RLS on exposed cognitive tables;
- no blanket `USING(true)` policies;
- event ledger with causation/correlation/idempotency fields;
- explicit claims rather than implicit world-state assertions;
- first-class evidence;
- temporal valid and record ranges;
- `state_type` included in belief/fact temporal uniqueness;
- surrogate relationship version IDs with temporal exclusion;
- reasoning runs and model contributions;
- epistemic gaps.

`pgvector` is enabled as an extension, but embeddings are deliberately treated as derived state rather than the canonical record.

## Cognitive continuity

AURORA's import pipeline is intended to become:

```text
RAW IMPORT
 → SOURCE METADATA
 → INTERACTION EVENTS
 → ASSERTIONS / CLAIMS
 → PROVENANCE
 → EVIDENCE ASSESSMENT
 → CANDIDATE MEMORY
 → PROMOTION / REJECTION
```

A historical model statement remains an attributed assertion rather than automatically becoming truth.

## Machine reincarnation

Essential cognitive state must survive infrastructure.

AURORA exports authoritative state separately from derived state. The target recovery test is:

```text
Machine A → export → portable state → fresh Machine B → import → verify → resume
```

The decisive question is:

> **Continue where we left off.**

## QUORUM

QUORUM is a subsystem, not a competing product identity.

It should be invoked when independent reasoning materially improves the result. Contributions remain attributable, disagreement is preserved, and future evaluation will measure whether QUORUM actually improves decision quality enough to justify its cost and latency.

## Developmental continuity

AURORA may eventually ingest selected development history — architecture decisions, experiments, failures and evaluations — as contextual evidence for future instances. This is intentionally separated from ordinary user/project knowledge.

## Master prompts

Current implementation instructions live in:

- `docs/prompts/AURORA_AGENT_MASTER_PROMPT.md`
- `docs/prompts/DEVELOPER_AGENT_MASTER_PROMPT_LEGACY.md`

The legacy prompt preserves the predecessor's DCA-era assumptions. It is historical reference, not the current contract.

## Architecture documents

- `docs/architecture/AURORA_MVP_ARCHITECTURE.md` — foundational architecture contract
- `docs/architecture/ARCHITECTURE_PRINCIPLES.md` — implementation invariants
- `docs/IMPLEMENTATION_STATUS.md` — executable scope and remaining MVP work
- `docs/PITCH_60_SECOND.md` — executive narrative
- `archive/predecessor/README.md` — lineage

## Roadmap

### Phase 0 — substrate correctness
Schema, tenancy, temporal semantics, event invariants and repository hygiene.

### Phase 1 — real cognitive loop
Persistent conversations, document ingestion, claims/evidence extraction, retrieval, reasoning and transparent traces.

### Phase 2 — continuity
Major LLM conversation importers, provenance reconstruction and memory promotion.

### Phase 3 — epistemic cognition
Facts vs beliefs, contradiction detection, confidence calibration, epistemic gaps and belief revision.

### Phase 4 — QUORUM
Independent contributions, cross-evaluation, disagreement representation, synthesis and contribution/cost ledger.

### Phase 5 — reincarnation
Complete export/import, schema versioning, checksums, rebuildable derived state and fresh-deployment resurrection.

### Later
UNBOX, richer control-plane visualisation, distributed event transport, autonomous agents and controlled self-improvement.

## Definition of done

AURORA is MVP-complete when it can take real conversations and documents through:

**Ask → Investigate → Reason → Explain → Remember**

while preserving evidence, provenance, uncertainty and cognitive history, and while surviving export/import into a fresh deployment.

## Lineage

AURORA is the clean implementation successor to `SystemVirtue/Supabase_Agentic_Assistant`. The predecessor is retained as an architectural R&D/archaeological layer rather than copied wholesale.

## Status

**Bootstrap → first executable cognitive substrate.**

The architecture is intentionally ahead of the implementation, but no unimplemented subsystem should be represented as finished merely because it exists in the architecture.
