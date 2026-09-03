-- Candidate claim provenance and contradiction helpers.
create index claims_workspace_status_idx on public.claims(workspace_id, assertion_status, created_at desc);
create index evidence_workspace_source_idx on public.evidence(workspace_id, source_id, created_at desc);

create or replace function public.claim_contradictions(target_workspace uuid)
returns table (claim_id uuid, opposing_claim_id uuid, subject text, predicate text, object text, opposing_object text)
language sql stable security invoker
set search_path = public
as $$
  select a.id, b.id, a.subject, a.predicate, a.object, b.object
  from public.claims a
  join public.claims b
    on b.workspace_id = a.workspace_id
   and b.id <> a.id
   and lower(b.subject) = lower(a.subject)
   and lower(b.predicate) = lower(a.predicate)
   and lower(b.object) <> lower(a.object)
  where a.workspace_id = target_workspace
    and a.assertion_status not in ('rejected','superseded')
    and b.assertion_status not in ('rejected','superseded');
$$;

comment on function public.claim_contradictions(uuid) is 'Finds competing non-rejected assertions sharing subject/predicate; it does not decide which is true.';
