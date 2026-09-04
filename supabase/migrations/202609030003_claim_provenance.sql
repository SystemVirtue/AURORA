-- Candidate claim provenance and contradiction helpers.
-- Evidence may now point to the exact derived document chunk that contains its excerpt.
alter table public.evidence
  add column if not exists document_chunk_id uuid references public.document_chunks(id) on delete set null;

create index if not exists evidence_workspace_chunk_idx
  on public.evidence(workspace_id, document_chunk_id, created_at desc);
create index if not exists claims_workspace_status_idx on public.claims(workspace_id, assertion_status, created_at desc);
create index if not exists evidence_workspace_source_idx on public.evidence(workspace_id, source_id, created_at desc);

create or replace function public.bind_evidence_chunk()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if new.document_chunk_id is null and new.excerpt is not null and length(trim(new.excerpt)) > 0 then
    select dc.id into new.document_chunk_id
      from public.document_chunks dc
      join public.documents d on d.id = dc.document_id
     where dc.workspace_id = new.workspace_id
       and (new.source_id is null or d.source_id = new.source_id)
       and position(trim(new.excerpt) in dc.content) > 0
     order by dc.chunk_index, dc.id
     limit 1;
  end if;
  return new;
end;
$$;

drop trigger if exists evidence_bind_chunk on public.evidence;
create trigger evidence_bind_chunk
before insert or update of excerpt, source_id, document_chunk_id on public.evidence
for each row execute function public.bind_evidence_chunk();

create or replace function public.claim_contradictions(target_workspace uuid)
returns table (claim_id uuid, opposing_claim_id uuid, subject text, predicate text, object text, opposing_object text)
language sql stable security invoker
set search_path = public
as $$
  select a.id, b.id, a.subject, a.predicate, a.object, b.object
  from public.claims a
  join public.claims b
    on b.workspace_id = a.workspace_id
   and b.id > a.id
   and lower(b.subject) = lower(a.subject)
   and lower(b.predicate) = lower(a.predicate)
   and lower(b.object) <> lower(a.object)
  where a.workspace_id = target_workspace
    and a.assertion_status not in ('rejected','superseded')
    and b.assertion_status not in ('rejected','superseded');
$$;

comment on function public.claim_contradictions(uuid) is 'Finds canonical pairs of competing non-rejected assertions sharing subject/predicate; it does not decide which is true.';
