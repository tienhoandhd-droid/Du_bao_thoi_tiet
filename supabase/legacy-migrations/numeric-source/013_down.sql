-- Rollback CRAVE Chat 10 - Citation Grounding
-- Chỉ hoàn nguyên các đối tượng do migration 013 tạo, không xóa chunk_id nếu cột đã tồn tại trước đó.

begin;

drop policy if exists insert_ai_query_sources_citation_grounding
  on public.ai_query_sources;

drop index if exists public.idx_ai_query_sources_cg_ungrounded;
drop index if exists public.idx_ai_query_sources_cg_query_rank;
drop index if exists public.idx_ai_query_sources_cg_chunk_id;

alter table if exists public.ai_query_sources
  drop constraint if exists ai_query_sources_cg_chunk_id_fkey,
  drop constraint if exists ai_query_sources_citation_rank_positive,
  drop constraint if exists ai_query_sources_claim_text_not_blank,
  drop constraint if exists ai_query_sources_grounded_requires_chunk;

do $$
declare
  column_note text;
begin
  if to_regclass('public.ai_query_sources') is null then
    return;
  end if;

  select col_description('public.ai_query_sources'::regclass, attnum)
    into column_note
  from pg_attribute
  where attrelid = 'public.ai_query_sources'::regclass
    and attname = 'citation_rank'
    and not attisdropped;

  if column_note like 'CRAVE-013:%' then
    alter table public.ai_query_sources drop column citation_rank;
  end if;

  select col_description('public.ai_query_sources'::regclass, attnum)
    into column_note
  from pg_attribute
  where attrelid = 'public.ai_query_sources'::regclass
    and attname = 'grounded'
    and not attisdropped;

  if column_note like 'CRAVE-013:%' then
    alter table public.ai_query_sources drop column grounded;
  end if;

  select col_description('public.ai_query_sources'::regclass, attnum)
    into column_note
  from pg_attribute
  where attrelid = 'public.ai_query_sources'::regclass
    and attname = 'claim_text'
    and not attisdropped;

  if column_note like 'CRAVE-013:%' then
    alter table public.ai_query_sources drop column claim_text;
  end if;

  select col_description('public.ai_query_sources'::regclass, attnum)
    into column_note
  from pg_attribute
  where attrelid = 'public.ai_query_sources'::regclass
    and attname = 'chunk_id'
    and not attisdropped;

  if column_note like 'CRAVE-013:%' then
    alter table public.ai_query_sources drop column chunk_id;
  end if;
end
$$;

commit;
