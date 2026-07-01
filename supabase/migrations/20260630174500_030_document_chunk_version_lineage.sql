-- CRAVE deploy migration: 20260630174500_030_document_chunk_version_lineage
-- Semantic source ID: CRAVE-030 / R05-A28 / BLK-006 prerequisite
-- Project: bdttccztjtrcaztjgkot
--
-- KHÔNG tự apply. Migration này backfill metadata trên document_chunks và cần
-- exact dry-run/change set/approval riêng trước khi `supabase db push --linked`.

begin;

do $preflight$
declare
  required_column text;
  existing_type text;
begin
  if to_regclass('public.documents') is null
    or to_regclass('public.document_versions') is null
    or to_regclass('public.document_chunks') is null
  then
    raise exception 'CRAVE-030: thiếu documents/document_versions/document_chunks.';
  end if;

  foreach required_column in array array['id', 'document_id', 'document_version', 'chunk_index']
  loop
    if not exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'document_chunks'
        and column_name = required_column
    ) then
      raise exception 'CRAVE-030: thiếu public.document_chunks.%.', required_column;
    end if;
  end loop;

  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'document_chunks'
      and column_name = 'document_version_id'
  ) then
    select c.udt_name into existing_type
    from information_schema.columns c
    where c.table_schema = 'public'
      and c.table_name = 'document_chunks'
      and c.column_name = 'document_version_id';

    if existing_type <> 'uuid' then
      raise exception 'CRAVE-030: document_version_id tồn tại nhưng không phải uuid.';
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
      raise exception 'CRAVE-030: document_version_id hiện có không mang marker CRAVE-030.';
    end if;
  end if;

  if to_regprocedure('public.crave_validate_document_chunk_version_lineage()') is not null
    and coalesce(
      obj_description(
        to_regprocedure('public.crave_validate_document_chunk_version_lineage()'),
        'pg_proc'
      ),
      ''
    ) not like 'CRAVE-030:%'
  then
    raise exception 'CRAVE-030: validator hiện có không mang marker CRAVE-030.';
  end if;
end
$preflight$;

alter table public.document_chunks
  add column if not exists document_version_id uuid;

comment on column public.document_chunks.document_version_id is
  'CRAVE-030: explicit immutable version lineage for every chunk; exact document/version match is trigger-enforced.';

do $ambiguity_guard$
declare
  ambiguous_pairs bigint;
  unmatched_chunks bigint;
  invalid_existing_links bigint;
begin
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

  select count(*) into unmatched_chunks
  from public.document_chunks dc
  where not exists (
    select 1
    from public.document_versions dv
    where dv.document_id = dc.document_id
      and dv.version_label = dc.document_version
  );

  select count(*) into invalid_existing_links
  from public.document_chunks dc
  left join public.document_versions dv on dv.id = dc.document_version_id
  where dc.document_version_id is not null
    and (
      dv.id is null
      or dv.document_id is distinct from dc.document_id
      or dv.version_label is distinct from dc.document_version
    );

  if ambiguous_pairs <> 0 or unmatched_chunks <> 0 or invalid_existing_links <> 0 then
    raise exception
      'CRAVE-030: lineage preflight fail ambiguous_pairs=% unmatched_chunks=% invalid_existing_links=%.',
      ambiguous_pairs, unmatched_chunks, invalid_existing_links;
  end if;
end
$ambiguity_guard$;

update public.document_chunks dc
set document_version_id = dv.id
from public.document_versions dv
where dc.document_version_id is null
  and dv.document_id = dc.document_id
  and dv.version_label = dc.document_version;

do $backfill_assert$
declare
  missing_links bigint;
  mismatched_links bigint;
begin
  select count(*) into missing_links
  from public.document_chunks
  where document_version_id is null;

  select count(*) into mismatched_links
  from public.document_chunks dc
  left join public.document_versions dv on dv.id = dc.document_version_id
  where dv.id is null
    or dv.document_id is distinct from dc.document_id
    or dv.version_label is distinct from dc.document_version;

  if missing_links <> 0 or mismatched_links <> 0 then
    raise exception 'CRAVE-030: backfill fail missing_links=% mismatched_links=%.',
      missing_links, mismatched_links;
  end if;
end
$backfill_assert$;

do $foreign_key$
begin
  if exists (
    select 1
    from pg_constraint
    where conrelid = 'public.document_chunks'::regclass
      and conname = 'document_chunks_document_version_id_fkey'
      and pg_get_constraintdef(oid) not like
        'FOREIGN KEY (document_version_id) REFERENCES document_versions(id)%'
  ) then
    raise exception 'CRAVE-030: FK cùng tên có definition không tương thích.';
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.document_chunks'::regclass
      and conname = 'document_chunks_document_version_id_fkey'
  ) then
    alter table public.document_chunks
      add constraint document_chunks_document_version_id_fkey
      foreign key (document_version_id)
      references public.document_versions(id)
      on update restrict
      on delete restrict;
  end if;
end
$foreign_key$;

comment on constraint document_chunks_document_version_id_fkey
  on public.document_chunks is
  'CRAVE-030: chunk must reference an immutable document_versions row.';

create or replace function public.crave_validate_document_chunk_version_lineage()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $function$
declare
  linked_document_id uuid;
  linked_version_label text;
begin
  if new.document_version_id is null then
    raise exception 'CRAVE-030: document_version_id bắt buộc cho document chunk.';
  end if;

  select dv.document_id, dv.version_label
  into linked_document_id, linked_version_label
  from public.document_versions dv
  where dv.id = new.document_version_id;

  if not found then
    raise exception 'CRAVE-030: document_version_id không tồn tại.';
  end if;
  if linked_document_id is distinct from new.document_id then
    raise exception 'CRAVE-030: chunk và immutable version khác logical document.';
  end if;
  if linked_version_label is distinct from new.document_version then
    raise exception 'CRAVE-030: document_version text không khớp immutable version.';
  end if;
  return new;
end
$function$;

comment on function public.crave_validate_document_chunk_version_lineage() is
  'CRAVE-030: enforce exact document_id/version_label/document_version_id lineage on document_chunks.';

drop trigger if exists document_chunks_validate_version_lineage
  on public.document_chunks;
create trigger document_chunks_validate_version_lineage
before insert or update of document_id, document_version, document_version_id
on public.document_chunks
for each row
execute function public.crave_validate_document_chunk_version_lineage();

alter table public.document_chunks
  alter column document_version_id set not null;

create index if not exists idx_document_chunks_document_version_id
  on public.document_chunks (document_version_id, chunk_index);

do $final_assert$
declare
  invalid_links bigint;
begin
  select count(*) into invalid_links
  from public.document_chunks dc
  join public.document_versions dv on dv.id = dc.document_version_id
  where dv.document_id is distinct from dc.document_id
    or dv.version_label is distinct from dc.document_version;

  if invalid_links <> 0 then
    raise exception 'CRAVE-030: final lineage assertion fail invalid_links=%.', invalid_links;
  end if;
end
$final_assert$;

commit;
