-- Belief revision is explicit, temporal, and event-auditable.
-- A review changes the status of a claim; promotion creates a temporal belief state.
create index beliefs_workspace_claim_idx
  on public.beliefs(workspace_id, claim_id, created_at desc);

create or replace function public.revise_claim(
  target_claim uuid,
  target_status text,
  reviewer uuid,
  target_confidence numeric default null,
  rationale text default null
)
returns uuid
language plpgsql
security invoker
set search_path = public
as $$
declare
  c claims%rowtype;
  b beliefs%rowtype;
  new_belief uuid;
  now_ts timestamptz := now();
begin
  if target_status not in ('unverified','supported','contested','rejected','superseded') then
    raise exception 'invalid assertion status: %', target_status;
  end if;

  select * into c
    from public.claims
   where id = target_claim
   for update;

  if not found then
    raise exception 'claim not found: %', target_claim;
  end if;

  if not public.is_workspace_member(c.workspace_id) then
    raise exception 'workspace access denied';
  end if;

  update public.claims
     set assertion_status = target_status,
         confidence = coalesce(target_confidence, confidence),
         metadata = metadata || jsonb_build_object(
           'last_reviewed_by', reviewer,
           'last_reviewed_at', now_ts,
           'review_rationale', rationale
         )
   where id = target_claim;

  if target_status in ('supported','contested') then
    -- Close the current open belief before inserting the replacement so the
    -- temporal exclusion constraint remains meaningful.
    select * into b
      from public.beliefs
     where claim_id = target_claim
       and workspace_id = c.workspace_id
       and upper_inf(valid_during)
     order by created_at desc
     limit 1
     for update;

    if found then
      update public.beliefs
         set valid_during = tstzrange(lower(valid_during), now_ts, '[)'),
             recorded_during = tstzrange(lower(recorded_during), now_ts, '[)')
       where id = b.id;
    end if;

    new_belief := gen_random_uuid();
    insert into public.beliefs
      (id, workspace_id, claim_id, state_type, confidence, valid_during, recorded_during)
    values
      (new_belief, c.workspace_id, c.id,
       case when target_status = 'supported' then 'fact' else 'belief' end,
       coalesce(target_confidence, c.confidence, 0),
       tstzrange(now_ts, null, '[)'),
       tstzrange(now_ts, null, '[)'));

    if found then
      update public.beliefs set superseded_by = new_belief where id = b.id;
    end if;
  end if;

  insert into public.events
    (workspace_id, event_type, producer_type, producer_id, event_time, recorded_at,
     schema_version, payload)
  values
    (c.workspace_id, 'claim.reviewed', 'human', reviewer, now_ts, now_ts, 1,
     jsonb_build_object('claim_id', c.id, 'status', target_status,
                        'confidence', target_confidence, 'rationale', rationale,
                        'belief_id', new_belief));

  return new_belief;
end;
$$;

comment on function public.revise_claim(uuid,text,uuid,numeric,text) is
  'Explicit human review of a claim. Supported/contested states create temporal belief versions; the function never silently resolves contradictions.';
