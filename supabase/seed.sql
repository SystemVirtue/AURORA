-- Local-only seed. Never include production/user data here.
-- The authenticated user/workspace fixture can be created by the local Supabase Auth UI.
-- This seed intentionally remains data-safe and does not fabricate an auth identity.

insert into public.workspaces (id, name, slug, created_by)
select '00000000-0000-0000-0000-000000000001', 'AURORA Development', 'aurora-development', id
from auth.users
where email = 'aurora@example.local'
  and not exists (select 1 from public.workspaces where slug = 'aurora-development');

insert into public.workspace_members (workspace_id, user_id, role)
select w.id, u.id, 'owner'
from public.workspaces w
join auth.users u on u.email = 'aurora@example.local'
where w.slug = 'aurora-development'
on conflict (workspace_id, user_id) do nothing;
