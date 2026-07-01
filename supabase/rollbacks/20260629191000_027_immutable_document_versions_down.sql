-- CRAVE rollback: 20260629191000_027_immutable_document_versions_down
-- Chỉ xóa legacy scaffold khi chưa có version/evidence/consumer mới.

begin;

do $guard$
declare
  unsafe_rows bigint;
  unexpected_rows bigint;
  consumer_fks bigint;
begin
  if to_regclass('public.document_versions') is null then
    return;
  end if;

  if coalesce(obj_description(to_regclass('public.document_versions'), 'pg_class'), '')
    not like 'CRAVE-027:%'
  then
    raise exception 'CRAVE-027 rollback: marker không khớp.';
  end if;

  select count(*) into unexpected_rows
  from public.document_versions
  where record_origin <> 'legacy_backfill_027';

  select count(*) into unsafe_rows
  from public.document_versions
  where record_origin='legacy_backfill_027'
    and (
      raw_file_id is not null
      or source_registry_id is not null
      or source_document_id is not null
      or source_updated_at is not null
      or retired_at is not null
      or superseded_by_version_id is not null
      or binary_sha256 is not null
      or content_sha256 is not null
      or hash_status <> 'legacy_missing'
      or license_status <> 'unknown'
      or parse_status <> 'needs_review'
      or parse_quality_score is not null
      or parse_engine is not null
      or parse_engine_version is not null
      or parsed_at is not null
      or parse_reviewed_by is not null
      or parse_reviewed_at is not null
      or approval_evidence_status <> 'missing'
      or approved_for_ai_use
      or approved_by is not null
      or approved_at is not null
      or index_status <> 'not_ready'
      or index_version is not null
    );

  select count(*) into consumer_fks
  from pg_constraint c
  where c.contype='f'
    and c.confrelid='public.document_versions'::regclass
    and c.conrelid <> 'public.documents'::regclass;

  if unexpected_rows <> 0 or unsafe_rows <> 0 or consumer_fks <> 0 then
    raise exception
      'CRAVE-027 rollback từ chối: unexpected=% evidence=% consumer_fks=%; dùng compatibility/manual recovery.',
      unexpected_rows, unsafe_rows, consumer_fks;
  end if;
end
$guard$;

update public.documents d
set current_version_id = null
where exists (
  select 1 from public.document_versions v
  where v.id=d.current_version_id and v.record_origin='legacy_backfill_027'
);

drop trigger if exists documents_validate_current_version on public.documents;
alter table public.documents
  drop constraint if exists documents_current_version_id_fkey,
  drop column if exists current_version_id;

drop trigger if exists document_versions_enforce_immutability
  on public.document_versions;
drop table if exists public.document_versions;
drop function if exists public.crave_validate_current_document_version();
drop function if exists public.crave_enforce_document_version_immutability();

commit;
