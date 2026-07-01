-- CRAVE-026 post-apply read-only catalog/data test.
begin;

do $test$
declare
  missing_legacy bigint;
  false_verified bigint;
begin
  if to_regclass('public.raw_files') is null then
    raise exception 'CRAVE-026 test: thiếu raw_files.';
  end if;

  if not exists (
    select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname='raw_files' and c.relrowsecurity
  ) then
    raise exception 'CRAVE-026 test: raw_files chưa bật RLS.';
  end if;

  if has_table_privilege('anon','public.raw_files','SELECT')
    or not has_table_privilege('authenticated','public.raw_files','SELECT')
  then
    raise exception 'CRAVE-026 test: table privileges sai.';
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid='public.raw_files'::regclass
      and conname in ('raw_files_sha256_check','raw_files_verified_check')
    group by conrelid having count(*)=2
  ) then
    raise exception 'CRAVE-026 test: thiếu hash/verified constraints.';
  end if;

  select count(*) into missing_legacy
  from public.drive_sync_log l
  where nullif(btrim(l.drive_file_id),'') is not null
    and not exists (
      select 1 from public.raw_files r where l.id=any(r.legacy_drive_sync_log_ids)
    );

  select count(*) into false_verified
  from public.raw_files
  where status='verified'
    and (hash_status<>'verified' or binary_sha256 is null or verified_at is null);

  if missing_legacy<>0 or false_verified<>0 then
    raise exception 'CRAVE-026 test: missing legacy=% false verified=%.',
      missing_legacy, false_verified;
  end if;
end
$test$;

rollback;
