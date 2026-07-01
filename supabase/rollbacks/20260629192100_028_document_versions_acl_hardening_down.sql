-- CRAVE rollback: 20260629192100_028_document_versions_acl_hardening_down
-- Khôi phục đúng ACL trước migration 028; reintroduce quyền rộng và chỉ được chạy
-- sau exact approval riêng.

begin;

do $preflight$
begin
  if to_regclass('public.document_versions') is null then
    raise exception 'CRAVE-028 rollback: thiếu document_versions.';
  end if;
end
$preflight$;

revoke all on table public.document_versions
  from authenticated, service_role;
grant all on table public.document_versions
  to authenticated, service_role;

commit;
