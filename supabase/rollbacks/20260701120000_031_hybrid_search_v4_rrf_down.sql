-- Rollback 031: gỡ hybrid_search_v4 (additive; v3 không bị ảnh hưởng).
begin;
drop function if exists public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
);
commit;
