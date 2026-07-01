-- Migration 023: Harden run_fts_eval_v1 SECURITY DEFINER boundary.
--
-- S1 read-only verification found the live function was SECURITY DEFINER but had
-- no locked search_path and was executable by anon via PUBLIC/default grants.
-- This migration does not change eval logic or existing eval data.

do $$
begin
  if to_regprocedure('public.run_fts_eval_v1(integer, text, text)') is null then
    raise exception 'Missing required function public.run_fts_eval_v1(integer, text, text); apply migrations through 022 first.';
  end if;
end $$;

alter function public.run_fts_eval_v1(integer, text, text)
  set search_path to pg_catalog, public, extensions;

revoke all on function public.run_fts_eval_v1(integer, text, text) from public;
revoke all on function public.run_fts_eval_v1(integer, text, text) from anon;

-- Keep intended automation/UI callers:
-- - GitHub eval workflow calls through service_role.
-- - Authenticated CRAVE users can still run the manual eval panel.
grant execute on function public.run_fts_eval_v1(integer, text, text) to authenticated;
grant execute on function public.run_fts_eval_v1(integer, text, text) to service_role;
