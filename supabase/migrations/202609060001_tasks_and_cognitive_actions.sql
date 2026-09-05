-- AURORA MVP action substrate: tasks connect goals to executable cognitive work.
create table public.tasks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  goal_id uuid references public.goals(id) on delete set null,
  title text not null,
  description text,
  status text not null default 'open' check (status in ('open','in_progress','blocked','completed','cancelled')),
  priority integer not null default 0,
  due_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index tasks_workspace_status_idx on public.tasks(workspace_id, status, priority desc, created_at);
create index tasks_goal_idx on public.tasks(goal_id);

alter table public.tasks enable row level security;
create policy tasks_select on public.tasks for select to authenticated
using (public.is_workspace_member(workspace_id));
create policy tasks_insert on public.tasks for insert to authenticated
with check (public.is_workspace_member(workspace_id));
create policy tasks_update on public.tasks for update to authenticated
using (public.is_workspace_member(workspace_id))
with check (public.is_workspace_member(workspace_id));
create policy tasks_delete on public.tasks for delete to authenticated
using (public.is_workspace_member(workspace_id));

comment on table public.tasks is 'MVP executable work items; durable action state linked to optional goals.';
