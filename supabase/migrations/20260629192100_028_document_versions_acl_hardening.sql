-- CRAVE deploy migration: 20260629192100_028_document_versions_acl_hardening
-- Semantic source ID: CRAVE-028 / R04-A02
-- Remediation tối thiểu cho Supabase default privileges sau migration 027.
-- KHÔNG tự apply; cần exact dry-run/change set/approval riêng.

begin;

do $preflight$
begin
  if to_regclass('public.document_versions') is null
    or coalesce(obj_description(to_regclass('public.document_versions'), 'pg_class'), '')
      not like 'CRAVE-027:%'
  then
    raise exception 'CRAVE-028: thiếu document_versions marker CRAVE-027.';
  end if;

  if not exists (
    select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname='document_versions' and c.relrowsecurity
  ) then
    raise exception 'CRAVE-028: document_versions chưa bật RLS.';
  end if;

  if to_regprocedure('public.crave_enforce_document_version_immutability()') is null
    or not exists (
      select 1 from pg_trigger
      where tgrelid='public.document_versions'::regclass
        and tgname='document_versions_enforce_immutability' and not tgisinternal
    )
  then
    raise exception 'CRAVE-028: thiếu immutability function/trigger.';
  end if;

  if not exists (select 1 from pg_roles where rolname='authenticated')
    or not exists (select 1 from pg_roles where rolname='service_role')
  then
    raise exception 'CRAVE-028: thiếu authenticated/service_role.';
  end if;
end
$preflight$;

revoke all on table public.document_versions
  from public, anon, authenticated, service_role;

grant select, insert, update on table public.document_versions
  to authenticated, service_role;

do $verify_acl$
begin
  if has_table_privilege('anon','public.document_versions','SELECT')
    or not has_table_privilege('authenticated','public.document_versions','SELECT')
    or not has_table_privilege('authenticated','public.document_versions','INSERT')
    or not has_table_privilege('authenticated','public.document_versions','UPDATE')
    or has_table_privilege('authenticated','public.document_versions','DELETE')
    or has_table_privilege('authenticated','public.document_versions','TRUNCATE')
    or has_table_privilege('authenticated','public.document_versions','REFERENCES')
    or has_table_privilege('authenticated','public.document_versions','TRIGGER')
    or not has_table_privilege('service_role','public.document_versions','SELECT')
    or not has_table_privilege('service_role','public.document_versions','INSERT')
    or not has_table_privilege('service_role','public.document_versions','UPDATE')
    or has_table_privilege('service_role','public.document_versions','DELETE')
    or has_table_privilege('service_role','public.document_versions','TRUNCATE')
    or has_table_privilege('service_role','public.document_versions','REFERENCES')
    or has_table_privilege('service_role','public.document_versions','TRIGGER')
  then
    raise exception 'CRAVE-028: ACL least-privilege verification thất bại.';
  end if;
end
$verify_acl$;

commit;
