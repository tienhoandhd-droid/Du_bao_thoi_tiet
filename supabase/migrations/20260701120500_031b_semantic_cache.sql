-- Migration 031b: semantic_cache — cache câu trả lời theo embedding truy vấn.
-- GMP-safe: cache tự VÔ HIỆU khi tài liệu nguồn bị hạ duyệt/đổi trạng thái
-- (không phục vụ câu trả lời từ SOP đã hết hiệu lực). Additive.

begin;

create table if not exists public.semantic_cache (
  id                  uuid primary key default gen_random_uuid(),
  query_text          text not null,
  query_embedding     extensions.vector(1536) not null,
  language_preference text not null default 'any',
  response            jsonb not null,            -- câu trả lời phân tầng + citations (JSON)
  cited_chunk_ids     uuid[] not null default '{}',
  cited_document_ids  uuid[] not null default '{}',
  created_by          uuid,
  created_at          timestamptz not null default now(),
  hit_count           integer not null default 0,
  is_valid            boolean not null default true,
  invalidated_at      timestamptz,
  invalidated_reason  text
);

comment on table public.semantic_cache is
  'CRAVE-031b: semantic cache câu trả lời (cosine>=ngưỡng). Tự vô hiệu khi tài liệu nguồn đổi trạng thái/hạ duyệt.';

create index if not exists idx_semantic_cache_valid
  on public.semantic_cache (is_valid, language_preference);
create index if not exists idx_semantic_cache_embedding
  on public.semantic_cache using hnsw (query_embedding extensions.vector_cosine_ops);

alter table public.semantic_cache enable row level security;

-- Đọc: authenticated chỉ thấy cache còn hiệu lực.
drop policy if exists semantic_cache_select on public.semantic_cache;
create policy semantic_cache_select on public.semantic_cache
  for select to authenticated
  using (is_valid = true);

-- Ghi mới: authenticated tự tạo (created_by = chính mình).
drop policy if exists semantic_cache_insert on public.semantic_cache;
create policy semantic_cache_insert on public.semantic_cache
  for insert to authenticated
  with check (created_by = auth.uid());

-- Không có policy UPDATE/DELETE cho authenticated → chỉ hàm SECURITY DEFINER
-- (invalidate) mới đổi is_valid; service_role giữ toàn quyền.

-- Tra cứu cache: trả hit hợp lệ có cosine >= ngưỡng (mặc định 0.8).
create or replace function public.semantic_cache_lookup_v1(
  p_query_embedding extensions.vector,
  p_threshold double precision default 0.8,
  p_language_preference text default 'any'
)
returns table(
  id uuid,
  query_text text,
  response jsonb,
  cited_chunk_ids uuid[],
  similarity double precision,
  created_at timestamptz
)
language sql
stable
security invoker
set search_path to 'pg_catalog', 'public', 'extensions'
as $function$
  select
    sc.id, sc.query_text, sc.response, sc.cited_chunk_ids,
    (1 - (sc.query_embedding <=> p_query_embedding)) as similarity,
    sc.created_at
  from public.semantic_cache sc
  where sc.is_valid = true
    and (p_language_preference = 'any' or sc.language_preference = p_language_preference)
    and (1 - (sc.query_embedding <=> p_query_embedding)) >= p_threshold
  order by sc.query_embedding <=> p_query_embedding
  limit 1;
$function$;

-- Vô hiệu cache theo tài liệu (gọi khi doc hạ duyệt/đổi trạng thái).
create or replace function public.semantic_cache_invalidate_for_document(
  p_document_id uuid,
  p_reason text default 'document_status_change'
)
returns integer
language plpgsql
security definer
set search_path to 'pg_catalog', 'public', 'extensions'
as $function$
declare
  v_count integer;
begin
  update public.semantic_cache sc
     set is_valid = false,
         invalidated_at = now(),
         invalidated_reason = p_reason
   where sc.is_valid = true
     and (
       p_document_id = any(sc.cited_document_ids)
       or exists (
         select 1 from public.document_chunks dc
         where dc.document_id = p_document_id
           and dc.id = any(sc.cited_chunk_ids)
       )
     );
  get diagnostics v_count = row_count;
  return v_count;
end;
$function$;

-- Trigger: khi documents đổi trạng thái duyệt/hiệu lực → vô hiệu cache liên quan.
create or replace function public.trg_semantic_cache_on_document_change()
returns trigger
language plpgsql
security definer
set search_path to 'pg_catalog', 'public', 'extensions'
as $function$
begin
  if (new.approved_for_ai_use is distinct from old.approved_for_ai_use)
     or (new.status is distinct from old.status)
     or (new.retired_date is distinct from old.retired_date)
     or (new.superseded_at is distinct from old.superseded_at) then
    perform public.semantic_cache_invalidate_for_document(new.id, 'document_change');
  end if;
  return new;
end;
$function$;

drop trigger if exists semantic_cache_invalidate_trg on public.documents;
create trigger semantic_cache_invalidate_trg
  after update on public.documents
  for each row
  execute function public.trg_semantic_cache_on_document_change();

grant execute on function public.semantic_cache_lookup_v1(extensions.vector, double precision, text)
  to authenticated, service_role;
grant execute on function public.semantic_cache_invalidate_for_document(uuid, text)
  to service_role;

commit;
