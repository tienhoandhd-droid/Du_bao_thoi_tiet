-- CRAVE compatibility rollback: 20260630174500_030_document_chunk_version_lineage
-- Không xóa chunk/version. Rollback chỉ bỏ explicit FK metadata sau khi chứng
-- minh legacy document_id + document_version text vẫn ánh xạ duy nhất.
-- KHÔNG tự chạy; cần exact approval riêng.

begin;

do $preflight$
declare
  unmatched_chunks bigint;
  ambiguous_pairs bigint;
begin
  if to_regclass('public.document_chunks') is null
    or to_regclass('public.document_versions') is null
  then
    raise exception 'CRAVE-030 rollback: thiếu document_chunks/document_versions.';
  end if;

  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'document_chunks'
      and column_name = 'document_version_id'
  ) then
    raise exception 'CRAVE-030 rollback: thiếu document_version_id.';
  end if;

  if coalesce(
    col_description('public.document_chunks'::regclass, (
      select attnum
      from pg_attribute
      where attrelid = 'public.document_chunks'::regclass
        and attname = 'document_version_id'
        and not attisdropped
    )),
    ''
  ) not like 'CRAVE-030:%' then
    raise exception 'CRAVE-030 rollback: column không mang marker CRAVE-030.';
  end if;

  select count(*) into unmatched_chunks
  from public.document_chunks dc
  where not exists (
    select 1
    from public.document_versions dv
    where dv.document_id = dc.document_id
      and dv.version_label = dc.document_version
  );

  select count(*) into ambiguous_pairs
  from (
    select dc.document_id, dc.document_version
    from public.document_chunks dc
    join public.document_versions dv
      on dv.document_id = dc.document_id
     and dv.version_label = dc.document_version
    group by dc.document_id, dc.document_version
    having count(distinct dv.id) <> 1
  ) ambiguous;

  if unmatched_chunks <> 0 or ambiguous_pairs <> 0 then
    raise exception
      'CRAVE-030 rollback: legacy compatibility unsafe unmatched_chunks=% ambiguous_pairs=%.',
      unmatched_chunks, ambiguous_pairs;
  end if;
end
$preflight$;

drop trigger if exists document_chunks_validate_version_lineage
  on public.document_chunks;
drop function if exists public.crave_validate_document_chunk_version_lineage();

alter table public.document_chunks
  drop constraint if exists document_chunks_document_version_id_fkey;
drop index if exists public.idx_document_chunks_document_version_id;
alter table public.document_chunks
  drop column document_version_id;

commit;
