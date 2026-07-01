-- Migration 031c: siết grant cho hybrid_search_v4 + semantic_cache functions.
-- Sửa lỗi: Supabase mặc định cấp execute cho anon → phải REVOKE FROM anon rõ ràng
-- (giống 030d cho v3). Giữ authenticated/service_role; anon bị chặn (fail-closed).

begin;

do $$
begin
  if to_regprocedure('public.hybrid_search_v4(extensions.vector,text,double precision,integer,uuid,text,text,text,integer,text,numeric,integer,integer)') is null then
    raise exception 'CRAVE-031C: hybrid_search_v4 signature not found';
  end if;
  if to_regprocedure('public.semantic_cache_lookup_v1(extensions.vector,double precision,text)') is null then
    raise exception 'CRAVE-031C: semantic_cache_lookup_v1 signature not found';
  end if;
  if to_regprocedure('public.semantic_cache_invalidate_for_document(uuid,text)') is null then
    raise exception 'CRAVE-031C: semantic_cache_invalidate_for_document signature not found';
  end if;
end
$$;

-- hybrid_search_v4: anon DENY, authenticated/service_role ALLOW.
revoke execute on function public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
) from anon, public;
grant execute on function public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
) to authenticated, service_role;

-- semantic_cache_lookup_v1: anon DENY, authenticated/service_role ALLOW.
revoke execute on function public.semantic_cache_lookup_v1(
  extensions.vector, double precision, text
) from anon, public;
grant execute on function public.semantic_cache_lookup_v1(
  extensions.vector, double precision, text
) to authenticated, service_role;

-- invalidate: chỉ service_role (anon + authenticated DENY).
revoke execute on function public.semantic_cache_invalidate_for_document(uuid, text)
  from anon, authenticated, public;
grant execute on function public.semantic_cache_invalidate_for_document(uuid, text)
  to service_role;

commit;
