-- Rollback 030d: remove authenticated direct execute grant for hybrid_search_v3.
-- Leaves pre-existing service_role/postgres privileges untouched.

begin;

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
) from authenticated;

commit;
