-- CRAVE deploy migration: 20260702090000_038_flagged_document_codes
-- Semantic source ID: CRAVE-038 / badge cờ trên kết quả tra cứu cho mọi user
-- Project: bdttccztjtrcaztjgkot
--
-- Frontend cần biết "document_code nào đang có cờ pending" để hiện badge cảnh báo
-- trên KẾT QUẢ TRA CỨU (mọi authenticated), nhưng CHI TIẾT mismatch vẫn chỉ QA
-- đọc được (view scan_flags_pending đã security_invoker/RLS ở 037).
-- Hàm này chỉ trả DANH SÁCH CODE (độ nhạy thấp), không lộ mismatch/evidence.

begin;

do $guard$
begin
  if to_regclass('public.scan_flag_queue') is null then
    raise exception 'CRAVE-038: thiếu public.scan_flag_queue (chạy 036 trước).';
  end if;
end
$guard$;

create or replace function public.flagged_document_codes()
returns setof text
language sql
stable
security definer
set search_path = public, extensions
as $$
  select distinct document_code
  from public.scan_flag_queue
  where status = 'AL_PROVISIONAL_PENDING_HUMAN'
    and document_code is not null;
$$;

comment on function public.flagged_document_codes() is
  'CRAVE-038: chỉ trả document_code đang có cờ pending — dùng cho badge cảnh báo trên kết quả tra cứu (mọi authenticated). Chi tiết mismatch/evidence vẫn hạn chế QA qua scan_flags_pending (RLS/security_invoker 037).';

revoke all on function public.flagged_document_codes() from public, anon;
grant execute on function public.flagged_document_codes() to authenticated, service_role;

commit;
