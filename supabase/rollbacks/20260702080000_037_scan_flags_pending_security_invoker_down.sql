-- Rollback CRAVE-037: trả view scan_flags_pending về quyền owner (mặc định).
begin;
alter view public.scan_flags_pending set (security_invoker = off);
commit;
