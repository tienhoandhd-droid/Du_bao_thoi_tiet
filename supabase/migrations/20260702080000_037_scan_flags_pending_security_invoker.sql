-- CRAVE deploy migration: 20260702080000_037_scan_flags_pending_security_invoker
-- Semantic source ID: CRAVE-037 / hardening RLS cho view hàng đợi cờ
-- Project: bdttccztjtrcaztjgkot
--
-- View public.scan_flags_pending (CRAVE-036) mặc định chạy quyền OWNER → bỏ qua
-- RLS của scan_flag_queue, khiến MỌI authenticated đọc được metadata cờ.
-- Đặt security_invoker=on để view chạy theo quyền NGƯỜI GỌI ⇒ policy
-- scan_flag_read_reviewer (created_by=auth.uid() HOẶC admin/qa_manager/auditor)
-- áp đúng. Không đổi cấu trúc dữ liệu; chỉ siết quyền đọc.

begin;

do $guard$
begin
  if to_regclass('public.scan_flags_pending') is null then
    raise exception 'CRAVE-037: thiếu view public.scan_flags_pending (chạy 036 trước).';
  end if;
end
$guard$;

alter view public.scan_flags_pending set (security_invoker = on);

commit;
