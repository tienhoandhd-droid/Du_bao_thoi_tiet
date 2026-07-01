-- CRAVE rollback artifact: 20260629182000_025_source_registry_license_gate_down
-- Semantic source ID: CRAVE-025 / R02-A01 / UPG-CHAT-03
--
-- Chỉ rollback khi source_registry còn đúng dữ liệu legacy fail-closed do 025
-- tạo và license_rules chưa có record. Nếu đã activation/rule mới, từ chối drop
-- và yêu cầu compatibility/roll-forward recovery để không mất evidence.
-- KHÔNG tự apply rollback nếu chưa có change-control và xác nhận riêng.

begin;

do $rollback_guard$
declare
  source_comment text;
  rule_comment text;
  unsafe_sources bigint := 0;
  rule_count bigint := 0;
begin
  if to_regclass('public.source_registry') is null
    and to_regclass('public.license_rules') is null
  then
    return;
  end if;

  if to_regclass('public.source_registry') is null
    or to_regclass('public.license_rules') is null
  then
    raise exception 'CRAVE-025 rollback: chỉ một trong hai bảng tồn tại; cần manual recovery.';
  end if;

  source_comment := obj_description('public.source_registry'::regclass, 'pg_class');
  rule_comment := obj_description('public.license_rules'::regclass, 'pg_class');

  if coalesce(source_comment, '') not like 'CRAVE-025:%'
    or coalesce(rule_comment, '') not like 'CRAVE-025:%'
  then
    raise exception 'CRAVE-025 rollback: target không mang marker CRAVE-025.';
  end if;

  select count(*) into rule_count from public.license_rules;

  select count(*)
  into unsafe_sources
  from public.source_registry
  where (
         cardinality(legacy_web_source_ids) = 0
         and cardinality(legacy_approved_source_ids) = 0
       )
       or is_active
       or approved_by is not null
       or approved_at is not null
       or access_mode <> 'metadata_only';

  if rule_count > 0 or unsafe_sources > 0 then
    raise exception
      'CRAVE-025 rollback refused: license_rules=%; non-legacy/activated/modified sources=%; use compatibility recovery.',
      rule_count,
      unsafe_sources;
  end if;
end
$rollback_guard$;

do $function_guard$
declare
  function_oid regprocedure := to_regprocedure('public.resolve_source_policy_v1(text,timestamp with time zone)');
  function_comment text;
begin
  if function_oid is null then
    return;
  end if;

  select obj_description(function_oid::oid, 'pg_proc') into function_comment;
  if coalesce(function_comment, '') not like 'CRAVE-025:%' then
    raise exception 'CRAVE-025 rollback: resolver không mang marker CRAVE-025.';
  end if;

  drop function public.resolve_source_policy_v1(text, timestamptz);
end
$function_guard$;

drop table if exists public.license_rules;
drop table if exists public.source_registry;

commit;
