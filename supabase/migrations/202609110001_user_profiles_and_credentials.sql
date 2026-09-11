create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  timezone text,
  default_model text,
  preferences jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_credentials (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null,
  label text not null,
  secret_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, provider, label)
);

alter table public.user_profiles enable row level security;
alter table public.user_credentials enable row level security;

create policy "user_profiles_self_select" on public.user_profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy "user_profiles_self_insert" on public.user_profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "user_profiles_self_update" on public.user_profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "user_credentials_self_select" on public.user_credentials for select to authenticated using ((select auth.uid()) = user_id);
create policy "user_credentials_self_insert" on public.user_credentials for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "user_credentials_self_update" on public.user_credentials for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "user_credentials_self_delete" on public.user_credentials for delete to authenticated using ((select auth.uid()) = user_id);

create index if not exists user_credentials_user_id_idx on public.user_credentials(user_id);
