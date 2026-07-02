-- Rollback CRAVE-036: scan_flag_queue + clear_scan_flag + view.
-- An toàn: chỉ gỡ đối tượng CRAVE-036 tạo ra. Dữ liệu cờ sẽ mất khi drop table.

begin;

drop function if exists public.clear_scan_flag(uuid, text, text);
drop view if exists public.scan_flags_pending;
drop table if exists public.scan_flag_queue;

commit;
