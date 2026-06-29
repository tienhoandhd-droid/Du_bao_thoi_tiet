-- Rollback for migration 023.
--
-- WARNING: this restores the insecure S1-observed function boundary:
-- - SECURITY DEFINER function has no explicit search_path config.
-- - Execute is reopened through PUBLIC/anon.
--
-- Use only under approved emergency change-control. This rollback does not
-- change eval logic or delete rows from eval_runs/eval_results.

do $$
begin
  if to_regprocedure('public.run_fts_eval_v1(integer, text, text)') is null then
    raise exception 'Missing required function public.run_fts_eval_v1(integer, text, text); cannot rollback migration 023.';
  end if;
end $$;

alter function public.run_fts_eval_v1(integer, text, text)
  reset search_path;

grant execute on function public.run_fts_eval_v1(integer, text, text) to public;
grant execute on function public.run_fts_eval_v1(integer, text, text) to anon;
grant execute on function public.run_fts_eval_v1(integer, text, text) to authenticated;
grant execute on function public.run_fts_eval_v1(integer, text, text) to service_role;
