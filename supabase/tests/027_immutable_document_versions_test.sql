-- CRAVE-027 post-apply read-only catalog/data test.
begin;

do $test$
declare
  document_count bigint;
  version_count bigint;
  missing_pointer bigint;
  bad_pointer bigint;
  false_legacy_evidence bigint;
begin
  if to_regclass('public.document_versions') is null then
    raise exception 'CRAVE-027 test: thiếu document_versions.';
  end if;

  if not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='documents'
      and column_name='current_version_id'
  ) then
    raise exception 'CRAVE-027 test: thiếu documents.current_version_id.';
  end if;

  if not exists (
    select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname='document_versions' and c.relrowsecurity
  ) then
    raise exception 'CRAVE-027 test: document_versions chưa bật RLS.';
  end if;

  if has_table_privilege('anon','public.document_versions','SELECT')
    or not has_table_privilege('authenticated','public.document_versions','SELECT')
    or has_table_privilege('authenticated','public.document_versions','DELETE')
  then
    raise exception 'CRAVE-027 test: table privileges sai.';
  end if;

  if not exists (
    select 1 from pg_trigger
    where tgrelid='public.document_versions'::regclass
      and tgname='document_versions_enforce_immutability' and not tgisinternal
  ) or not exists (
    select 1 from pg_trigger
    where tgrelid='public.documents'::regclass
      and tgname='documents_validate_current_version' and not tgisinternal
  ) then
    raise exception 'CRAVE-027 test: thiếu immutability/current-pointer trigger.';
  end if;

  select count(*) into document_count from public.documents;
  select count(*) into version_count
  from public.document_versions where record_origin='legacy_backfill_027';

  select count(*) into missing_pointer
  from public.documents where current_version_id is null;

  select count(*) into bad_pointer
  from public.documents d
  left join public.document_versions v on v.id=d.current_version_id
  where v.document_id is distinct from d.id or v.superseded_by_version_id is not null;

  select count(*) into false_legacy_evidence
  from public.document_versions
  where record_origin='legacy_backfill_027'
    and (
      raw_file_id is not null
      or binary_sha256 is not null
      or content_sha256 is not null
      or hash_status <> 'legacy_missing'
      or approval_evidence_status <> 'missing'
      or approved_for_ai_use
      or parse_status <> 'needs_review'
      or index_status <> 'not_ready'
    );

  if document_count <> version_count
    or missing_pointer <> 0
    or bad_pointer <> 0
    or false_legacy_evidence <> 0
  then
    raise exception
      'CRAVE-027 test: documents=% versions=% missing_pointer=% bad_pointer=% false_evidence=%.',
      document_count, version_count, missing_pointer, bad_pointer, false_legacy_evidence;
  end if;
end
$test$;

rollback;
