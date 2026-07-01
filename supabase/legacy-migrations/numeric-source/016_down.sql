-- CRAVE - Rollback Migration 016
-- Drop the dependent table before its parent. Safe to run repeatedly.

begin;

drop table if exists public.eval_results cascade;
drop table if exists public.eval_runs cascade;

commit;
