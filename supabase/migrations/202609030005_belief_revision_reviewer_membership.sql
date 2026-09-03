-- Make claim review safe for the direct-DB API path as well as Supabase RLS.
-- The API authenticates the reviewer and checks workspace membership before calling
-- revise_claim. The function must also authorize the explicit reviewer UUID rather
-- than relying on auth.uid(), which is not populated on a direct psycopg connection.
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
  old_belief_id uuid;
  new_belief uuid;
  now_ts timestamptz := now();
begin
  if target_status not in ('unverified','supported','contested','rejected','superseded') then
    raise exception 'invalid assertion status: %', target_status;
  end if;

  select * into c from public.claims where id = target_claim for update;
  if not found then raise exception 'claim not found: %', target_claim; end if;

  -- Direct psycopg connections do not carry a Supabase auth.uid() context.
  -- Authorize the explicit reviewer against the same workspace instead.
  if not exists (
    select 1
      from public.workspace_members wm
     where wm.workspace_id = c.workspace_id
       and wm.user_id = reviewer
  ) then
    raise exception 'reviewer is not a workspace member';
  end if;

  update public.claims
     set assertion_status = target_status,
         confidence = coalesce(target_confidence, confidence),
         metadata = metadata || jsonb_build_object(
           'last_reviewed_by', reviewer,
           'last_reviewed_at', now_ts,
           'review_rationale', rationale)
   where id = target_claim;

  if target_status in ('supported','contested') then
    select id into old_belief_id
      from public.beliefs
     where claim_id = target_claim
       and workspace_id = c.workspace_id
       and upper_inf(valid_during)
     order by created_at desc
     limit 1
     for update;

    if old_belief_id is not null then
      update public.beliefs
         set valid_during = tstzrange(lower(valid_during), now_ts, '[)'),
             recorded_during = tstzrange(lower(recorded_during), now_ts, '[)')
       where id = old_belief_id;
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

    if old_belief_id is not null then
      update public.beliefs set superseded_by = new_belief where id = old_belief_id;
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
  'Explicit human review of a claim. Supported/contested states create temporal belief versions; reviewer must belong to the claim workspace.';
