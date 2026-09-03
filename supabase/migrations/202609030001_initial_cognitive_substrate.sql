-- AURORA initial cognitive substrate
-- Canonical primitives: identity, events, claims, evidence, cognition.
-- Valid-time and record-time semantics are explicit.

create extension if not exists pgcrypto;
create extension if not exists btree_gist;
create extension if not exists vector;

create table public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','member','viewer')),
  created_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

create index workspace_members_user_idx on public.workspace_members(user_id, workspace_id);

create table public.sources (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  source_type text not null check (source_type in ('human','model','document','web','system','derived')),
  name text,
  provider text,
  external_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  title text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  session_id uuid references public.sessions(id) on delete set null,
  event_type text not null,
  producer_type text not null check (producer_type in ('human','model','system','integration')),
  producer_id uuid,
  event_time timestamptz not null default now(),
  recorded_at timestamptz not null default now(),
  causation_id uuid references public.events(id) on delete set null,
  correlation_id uuid,
  aggregate_type text,
  aggregate_id uuid,
  schema_version integer not null default 1,
  idempotency_key text,
  payload jsonb not null default '{}'::jsonb
);

create unique index events_idempotency_idx on public.events(workspace_id, idempotency_key) where idempotency_key is not null;
create index events_workspace_time_idx on public.events(workspace_id, recorded_at desc);
create index events_correlation_idx on public.events(correlation_id);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  session_id uuid not null references public.sessions(id) on delete cascade,
  event_id uuid references public.events(id) on delete set null,
  role text not null check (role in ('system','user','assistant','tool')),
  content text not null,
  source_id uuid references public.sources(id) on delete set null,
  sequence_no bigint not null,
  created_at timestamptz not null default now(),
  unique(session_id, sequence_no)
);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  source_id uuid not null references public.sources(id) on delete restrict,
  name text not null,
  mime_type text,
  content text,
  content_hash text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index documents_workspace_idx on public.documents(workspace_id);

create table public.claims (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  source_id uuid references public.sources(id) on delete set null,
  event_id uuid references public.events(id) on delete set null,
  subject text not null,
  predicate text not null,
  object text not null,
  assertion_status text not null default 'unverified' check (assertion_status in ('unverified','supported','contested','rejected','superseded')),
  confidence numeric(5,4) check (confidence between 0 and 1),
  valid_during tstzrange not null default tstzrange(now(), null, '[)'),
  recorded_during tstzrange not null default tstzrange(now(), null, '[)'),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index claims_workspace_subject_idx on public.claims(workspace_id, subject);
create index claims_valid_idx on public.claims using gist(valid_during);
create index claims_recorded_idx on public.claims using gist(recorded_during);

create table public.evidence (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  claim_id uuid not null references public.claims(id) on delete cascade,
  source_id uuid references public.sources(id) on delete set null,
  event_id uuid references public.events(id) on delete set null,
  relation text not null check (relation in ('supports','contradicts','qualifies','contextualizes')),
  strength numeric(5,4) check (strength between 0 and 1),
  extraction_method text,
  excerpt text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index evidence_claim_idx on public.evidence(claim_id);

create table public.entities (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  entity_type text not null,
  canonical_name text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(workspace_id, entity_type, canonical_name)
);

create table public.relationships (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  source_entity_id uuid not null references public.entities(id) on delete cascade,
  target_entity_id uuid not null references public.entities(id) on delete cascade,
  rel_type text not null,
  valid_during tstzrange not null default tstzrange(now(), null, '[)'),
  recorded_during tstzrange not null default tstzrange(now(), null, '[)'),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (source_entity_id <> target_entity_id),
  exclude using gist (workspace_id with =, source_entity_id with =, target_entity_id with =, rel_type with =, valid_during with &&)
);

create table public.beliefs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  claim_id uuid not null references public.claims(id) on delete cascade,
  state_type text not null check (state_type in ('fact','belief')),
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  valid_during tstzrange not null default tstzrange(now(), null, '[)'),
  recorded_during tstzrange not null default tstzrange(now(), null, '[)'),
  superseded_by uuid references public.beliefs(id) on delete set null,
  created_at timestamptz not null default now(),
  exclude using gist (workspace_id with =, claim_id with =, state_type with =, valid_during with &&)
);

create table public.memories (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  claim_id uuid references public.claims(id) on delete set null,
  memory_type text not null check (memory_type in ('episodic','semantic','procedural','project')),
  status text not null default 'candidate' check (status in ('candidate','active','superseded','rejected')),
  confidence numeric(5,4) check (confidence between 0 and 1),
  rationale text,
  created_at timestamptz not null default now(),
  last_confirmed_at timestamptz,
  superseded_by uuid references public.memories(id) on delete set null
);

create table public.goals (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null,
  description text,
  status text not null default 'active' check (status in ('active','paused','completed','cancelled')),
  priority integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.decisions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  event_id uuid references public.events(id) on delete set null,
  title text not null,
  decision text not null,
  rationale text,
  confidence numeric(5,4) check (confidence between 0 and 1),
  created_at timestamptz not null default now()
);

create table public.reasoning_runs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  session_id uuid references public.sessions(id) on delete set null,
  question text not null,
  mode text not null default 'balanced' check (mode in ('fast','balanced','deep','quorum')),
  status text not null default 'started' check (status in ('started','completed','failed','cancelled')),
  answer text,
  confidence numeric(5,4) check (confidence between 0 and 1),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table public.model_contributions (
  id uuid primary key default gen_random_uuid(),
  reasoning_run_id uuid not null references public.reasoning_runs(id) on delete cascade,
  model_id text not null,
  provider text,
  role text not null default 'reasoner',
  response text not null,
  confidence numeric(5,4) check (confidence between 0 and 1),
  latency_ms integer,
  estimated_cost numeric(12,6),
  evidence_ids uuid[] not null default '{}',
  created_at timestamptz not null default now()
);

create table public.epistemic_gaps (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  reasoning_run_id uuid references public.reasoning_runs(id) on delete set null,
  claim_id uuid references public.claims(id) on delete set null,
  description text not null,
  gap_type text not null check (gap_type in ('missing_evidence','contradiction','stale','low_confidence','unanswered','verification_required')),
  severity numeric(5,4) check (severity between 0 and 1),
  resolution_hint text,
  status text not null default 'open' check (status in ('open','resolved','accepted')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

-- RLS: workspace membership is the authorization boundary.
-- Do not use USING(true)/WITH CHECK(true) for cognitive data.

create or replace function public.is_workspace_member(target_workspace uuid)
returns boolean
language sql
stable
security invoker
set search_path = public
as $$
  select exists (
    select 1 from public.workspace_members wm
    where wm.workspace_id = target_workspace
      and wm.user_id = (select auth.uid())
  );
$$;

alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.sources enable row level security;
alter table public.sessions enable row level security;
alter table public.events enable row level security;
alter table public.messages enable row level security;
alter table public.documents enable row level security;
alter table public.claims enable row level security;
alter table public.evidence enable row level security;
alter table public.entities enable row level security;
alter table public.relationships enable row level security;
alter table public.beliefs enable row level security;
alter table public.memories enable row level security;
alter table public.goals enable row level security;
alter table public.decisions enable row level security;
alter table public.reasoning_runs enable row level security;
alter table public.model_contributions enable row level security;
alter table public.epistemic_gaps enable row level security;

create policy workspace_select on public.workspaces for select to authenticated
using (public.is_workspace_member(id));
create policy workspace_insert on public.workspaces for insert to authenticated
with check ((select auth.uid()) = created_by);
create policy workspace_update on public.workspaces for update to authenticated
using (public.is_workspace_member(id)) with check (public.is_workspace_member(id));

create policy member_select on public.workspace_members for select to authenticated
using (public.is_workspace_member(workspace_id));
create policy member_insert on public.workspace_members for insert to authenticated
with check (public.is_workspace_member(workspace_id));
create policy member_update on public.workspace_members for update to authenticated
using (public.is_workspace_member(workspace_id)) with check (public.is_workspace_member(workspace_id));
create policy member_delete on public.workspace_members for delete to authenticated
using (public.is_workspace_member(workspace_id));

-- Uniform workspace policies for cognitive tables.
do $$
declare
  t text;
begin
  foreach t in array array['sources','sessions','events','messages','documents','claims','evidence','entities','relationships','beliefs','memories','goals','decisions','reasoning_runs','epistemic_gaps'] loop
    execute format('create policy %I_select on public.%I for select to authenticated using (public.is_workspace_member(workspace_id))', t, t);
    execute format('create policy %I_insert on public.%I for insert to authenticated with check (public.is_workspace_member(workspace_id))', t, t);
    execute format('create policy %I_update on public.%I for update to authenticated using (public.is_workspace_member(workspace_id)) with check (public.is_workspace_member(workspace_id))', t, t);
    execute format('create policy %I_delete on public.%I for delete to authenticated using (public.is_workspace_member(workspace_id))', t, t);
  end loop;
end $$;

create policy contribution_select on public.model_contributions for select to authenticated
using (exists (select 1 from public.reasoning_runs rr where rr.id = reasoning_run_id and public.is_workspace_member(rr.workspace_id)));
create policy contribution_insert on public.model_contributions for insert to authenticated
with check (exists (select 1 from public.reasoning_runs rr where rr.id = reasoning_run_id and public.is_workspace_member(rr.workspace_id)));
create policy contribution_update on public.model_contributions for update to authenticated
using (exists (select 1 from public.reasoning_runs rr where rr.id = reasoning_run_id and public.is_workspace_member(rr.workspace_id)))
with check (exists (select 1 from public.reasoning_runs rr where rr.id = reasoning_run_id and public.is_workspace_member(rr.workspace_id)));
create policy contribution_delete on public.model_contributions for delete to authenticated
using (exists (select 1 from public.reasoning_runs rr where rr.id = reasoning_run_id and public.is_workspace_member(rr.workspace_id)));

comment on table public.events is 'Canonical durable cognitive history. State projections must remain reconstructible from this ledger where practical.';
comment on table public.claims is 'Atomic assertions. A model assertion remains unverified unless separately supported.';
comment on table public.evidence is 'First-class provenance links between claims and sources/events.';
comment on table public.beliefs is 'Temporal cognitive state; state_type deliberately participates in the non-overlap constraint.';
comment on table public.relationships is 'Temporal relationship versions use surrogate IDs and exclusion constraints rather than a fixed logical PK.';
