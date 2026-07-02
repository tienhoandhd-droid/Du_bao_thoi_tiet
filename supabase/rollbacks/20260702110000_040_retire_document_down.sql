-- Rollback CRAVE-040: gỡ 2 hàm vòng đời (không đụng dữ liệu tài liệu).
begin;
drop function if exists public.retire_document(uuid, text);
drop function if exists public.reactivate_document(uuid);
commit;
