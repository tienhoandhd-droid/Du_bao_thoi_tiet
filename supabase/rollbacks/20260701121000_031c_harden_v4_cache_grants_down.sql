-- Rollback 031c: khôi phục grant execute cho public (trở lại trạng thái trước siết).
-- Lưu ý: đây là nới lỏng, chỉ dùng nếu cần hoàn tác chủ đích.
begin;
grant execute on function public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
) to public;
grant execute on function public.semantic_cache_lookup_v1(
  extensions.vector, double precision, text
) to public;
commit;
