-- Migration 030d: allow authenticated user-JWT RPC execution for hybrid_search_v3.
-- CRAVE R05-A41 remediation: keep anon denied; retrieval authorization remains
-- inside hybrid_search_v3 via p_user_id/document access/current-version gates.

begin;

do $$
declare
  target_oid oid;
begin
  target_oid := to_regprocedure(
    'public.hybrid_search_v3(extensions.vector,text,double precision,integer,uuid,text,text,text,integer,text,numeric)'
  );

  if target_oid is null then
    raise exception 'CRAVE-030D: expected public.hybrid_search_v3(extensions.vector,text,double precision,integer,uuid,text,text,text,integer,text,numeric) signature not found';
  end if;

  revoke execute on function public.hybrid_search_v3(
    extensions.vector,
    text,
    double precision,
    integer,
    uuid,
    text,
    text,
    text,
    integer,
    text,
    numeric
  ) from public;

  revoke execute on function public.hybrid_search_v3(
    extensions.vector,
    text,
    double precision,
    integer,
    uuid,
    text,
    text,
    text,
    integer,
    text,
    numeric
  ) from anon;

  grant execute on function public.hybrid_search_v3(
    extensions.vector,
    text,
    double precision,
    integer,
    uuid,
    text,
    text,
    text,
    integer,
    text,
    numeric
  ) to authenticated;
end
$$;

commit;
