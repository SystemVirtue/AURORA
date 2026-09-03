-- AURORA retrieval projection. Chunks are derived from source documents but remain
-- durable enough to reproduce retrieval results and rebuild embeddings later.
create table public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index integer not null check (chunk_index >= 0),
  content text not null,
  content_hash text not null,
  token_estimate integer,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);

create index document_chunks_workspace_idx on public.document_chunks(workspace_id);
create index document_chunks_document_idx on public.document_chunks(document_id, chunk_index);
create index document_chunks_fts_idx on public.document_chunks using gin (to_tsvector('simple', content));
create index document_chunks_embedding_idx on public.document_chunks using hnsw (embedding vector_cosine_ops);

alter table public.document_chunks enable row level security;
create policy document_chunks_select on public.document_chunks for select to authenticated
using (public.is_workspace_member(workspace_id));
create policy document_chunks_insert on public.document_chunks for insert to authenticated
with check (public.is_workspace_member(workspace_id));
create policy document_chunks_update on public.document_chunks for update to authenticated
using (public.is_workspace_member(workspace_id)) with check (public.is_workspace_member(workspace_id));
create policy document_chunks_delete on public.document_chunks for delete to authenticated
using (public.is_workspace_member(workspace_id));

comment on table public.document_chunks is 'Durable retrieval projection; embeddings are derived and rebuildable.';
