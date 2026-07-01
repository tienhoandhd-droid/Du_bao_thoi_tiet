-- CRAVE rollback: 20260629184000_026_raw_file_lineage_down
-- Chỉ drop khi toàn bộ row vẫn là legacy_unverified/legacy_missing và không có
-- source/document/hash evidence mới. Nếu đã dùng, từ chối destructive rollback.

begin;

do $guard$
declare
  table_comment text;
  unsafe_rows bigint;
begin
  if to_regclass('public.raw_files') is null then return; end if;

  table_comment := obj_description('public.raw_files'::regclass, 'pg_class');
  if coalesce(table_comment, '') not like 'CRAVE-026:%' then
    raise exception 'CRAVE-026 rollback: raw_files thiếu marker.';
  end if;

  select count(*) into unsafe_rows
  from public.raw_files
  where status <> 'legacy_unverified'
     or hash_status <> 'legacy_missing'
     or binary_sha256 is not null
     or verified_at is not null
     or source_registry_id is not null
     or (
       cardinality(legacy_gdrive_source_ids) = 0
       and cardinality(legacy_drive_sync_log_ids) = 0
     );

  if unsafe_rows > 0 then
    raise exception 'CRAVE-026 rollback refused: % non-legacy/verified/linked rows; use compatibility recovery.', unsafe_rows;
  end if;
end
$guard$;

drop table if exists public.raw_files;

commit;
