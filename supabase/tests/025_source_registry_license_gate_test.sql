-- CRAVE-025 post-apply read-only/catalog test. Không tạo/sửa dữ liệu.
begin;

do $catalog$
declare
  missing text;
  function_oid regprocedure;
  function_comment text;
begin
  if to_regclass('public.source_registry') is null
    or to_regclass('public.license_rules') is null
  then
    raise exception 'CRAVE-025 test: thiếu bảng target.';
  end if;

  select string_agg(required_column, ', ' order by required_column)
  into missing
  from unnest(array[
    'access_mode','approved_at','approved_by','domain','effective_from',
    'effective_until','is_active','legacy_approved_source_ids',
    'legacy_web_source_ids','seed_urls','source_name'
  ]) required_column
  where not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'source_registry'
      and column_name = required_column
  );

  if missing is not null then
    raise exception 'CRAVE-025 test: source_registry thiếu cột %.', missing;
  end if;

  if not exists (
    select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'source_registry' and c.relrowsecurity
  ) or not exists (
    select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'license_rules' and c.relrowsecurity
  ) then
    raise exception 'CRAVE-025 test: RLS chưa bật cho cả hai bảng.';
  end if;

  if not exists (
    select 1 from pg_trigger
    where tgrelid = 'public.license_rules'::regclass
      and tgname = 'license_rules_append_only_guard'
      and not tgisinternal
  ) then
    raise exception 'CRAVE-025 test: thiếu append-only trigger.';
  end if;

  function_oid := to_regprocedure('public.resolve_source_policy_v1(text,timestamp with time zone)');
  if function_oid is null then
    raise exception 'CRAVE-025 test: thiếu resolver signature.';
  end if;

  select obj_description(function_oid::oid, 'pg_proc') into function_comment;
  if coalesce(function_comment, '') not like 'CRAVE-025:%' then
    raise exception 'CRAVE-025 test: resolver thiếu marker.';
  end if;

  if exists (
    select 1 from pg_proc p
    where p.oid = function_oid::oid
      and (p.prosecdef or p.provolatile <> 's'
           or not coalesce(p.proconfig, '{}') @> array['search_path=pg_catalog, public'])
  ) then
    raise exception 'CRAVE-025 test: resolver phải STABLE, SECURITY INVOKER, locked search_path.';
  end if;
end
$catalog$;

do $authorization$
begin
  if has_table_privilege('anon', 'public.source_registry', 'SELECT')
    or has_table_privilege('anon', 'public.license_rules', 'SELECT')
    or has_function_privilege(
      'anon',
      'public.resolve_source_policy_v1(text,timestamp with time zone)',
      'EXECUTE'
    )
  then
    raise exception 'CRAVE-025 test: anon không được quyền đọc/execute.';
  end if;

  if not has_table_privilege('authenticated', 'public.source_registry', 'SELECT')
    or not has_table_privilege('authenticated', 'public.license_rules', 'SELECT')
    or not has_function_privilege(
      'authenticated',
      'public.resolve_source_policy_v1(text,timestamp with time zone)',
      'EXECUTE'
    )
  then
    raise exception 'CRAVE-025 test: authenticated thiếu quyền contract.';
  end if;

  if exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename in ('source_registry','license_rules')
      and 'public' = any(roles)
  ) then
    raise exception 'CRAVE-025 test: policy không được gán role public.';
  end if;
end
$authorization$;

do $legacy$
declare
  missing_legacy bigint;
  unsafe_legacy bigint;
begin
  select count(*) into missing_legacy
  from public.web_sources w
  where nullif(btrim(w.base_url), '') is not null
    and not exists (
      select 1 from public.source_registry s
      where w.id = any(s.legacy_web_source_ids)
    );

  select count(*) into unsafe_legacy
  from public.source_registry s
  where cardinality(s.legacy_web_source_ids) > 0
    and (s.is_active or s.access_mode <> 'metadata_only');

  if missing_legacy <> 0 or unsafe_legacy <> 0 then
    raise exception 'CRAVE-025 test: missing legacy=%; unsafe legacy=%.', missing_legacy, unsafe_legacy;
  end if;
end
$legacy$;

set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000001', true);

do $fail_closed$
declare
  result jsonb;
begin
  result := public.resolve_source_policy_v1('https://unknown.invalid/example.pdf', now());
  if result->>'decision' <> 'deny'
    or coalesce((result->>'allow_fetch')::boolean, true)
    or coalesce((result->>'matched')::boolean, true)
  then
    raise exception 'CRAVE-025 test: unknown source không fail closed: %', result;
  end if;
end
$fail_closed$;

rollback;
