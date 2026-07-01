-- CRAVE rollback: 20260630221500_030c_eval_v2_health_gate
-- Chỉ rollback khi chưa có v2 dataset/run/result/failure evidence.

begin;

do $rollback_guard$
declare
  row_count bigint;
begin
  if to_regclass('public.eval_datasets') is not null then
    select count(*) into row_count from public.eval_datasets;
    if row_count <> 0 then
      raise exception
        'CRAVE-030C rollback từ chối: eval_datasets có % rows.', row_count;
    end if;
  end if;

  if to_regclass('public.eval_failures') is not null then
    select count(*) into row_count from public.eval_failures;
    if row_count <> 0 then
      raise exception
        'CRAVE-030C rollback từ chối: eval_failures có % rows.', row_count;
    end if;
  end if;

  if exists (
    select 1 from public.eval_runs
    where eval_contract_version = 'v2'
  ) then
    raise exception 'CRAVE-030C rollback từ chối: eval_runs đã có v2 evidence.';
  end if;

  if exists (
    select 1
    from public.eval_results result
    join public.eval_runs run on run.id = result.run_id
    where run.eval_contract_version = 'v2'
  ) then
    raise exception 'CRAVE-030C rollback từ chối: eval_results đã có v2 evidence.';
  end if;
end
$rollback_guard$;

drop trigger if exists eval_datasets_append_only_guard on public.eval_datasets;
drop trigger if exists eval_runs_append_only_guard on public.eval_runs;
drop trigger if exists eval_results_append_only_guard on public.eval_results;
drop trigger if exists eval_failures_append_only_guard on public.eval_failures;

drop policy if exists eval_runs_read_auditor on public.eval_runs;
drop policy if exists eval_results_read_auditor on public.eval_results;

drop trigger if exists eval_failures_validate_context on public.eval_failures;
drop trigger if exists eval_results_validate_v2_context on public.eval_results;
drop trigger if exists eval_runs_validate_v2_context on public.eval_runs;

drop function if exists public.crave_evaluate_system_health_gate_v1(text[], interval);
drop function if exists public.crave_evaluate_eval_v2_release_gate_v1(uuid);
drop function if exists public.crave_validate_eval_failure_context();
drop function if exists public.crave_validate_eval_result_v2_context();
drop function if exists public.crave_validate_eval_run_v2_context();

drop index if exists public.idx_eval_results_run_question_unique;

drop table if exists public.eval_failures;

alter table if exists public.eval_results
  drop constraint if exists eval_results_v2_metric_ranges_check,
  drop constraint if exists eval_results_ai_query_id_fkey,
  drop constraint if exists eval_results_retrieval_log_id_fkey,
  drop column if exists evaluation_summary,
  drop column if exists latency_ms,
  drop column if exists tool_policy_pass,
  drop column if exists version_freshness_pass,
  drop column if exists permission_pass,
  drop column if exists citation_grounding_score,
  drop column if exists stale_version_count,
  drop column if exists permission_leakage_count,
  drop column if exists ai_query_id,
  drop column if exists retrieval_log_id;

alter table if exists public.eval_runs
  drop constraint if exists eval_runs_v2_lineage_check,
  drop constraint if exists eval_runs_parameters_check,
  drop constraint if exists eval_runs_status_check,
  drop constraint if exists eval_runs_contract_version_check,
  drop constraint if exists eval_runs_retrieval_profile_id_fkey,
  drop constraint if exists eval_runs_dataset_id_fkey,
  drop column if exists parameters,
  drop column if exists completed_at,
  drop column if exists started_at,
  drop column if exists run_status,
  drop column if exists release_candidate,
  drop column if exists git_commit_sha,
  drop column if exists workflow_version,
  drop column if exists workflow_name,
  drop column if exists retrieval_profile_id,
  drop column if exists dataset_id,
  drop column if exists eval_contract_version;

drop table if exists public.eval_datasets;

grant insert on table public.eval_runs, public.eval_results to authenticated;
grant execute on function public.run_fts_eval_v1(integer, text, text)
to authenticated;

do $restore_legacy_insert_policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_runs'
      and policyname = 'eval_runs_select_authenticated'
  ) then
    create policy eval_runs_select_authenticated
      on public.eval_runs for select to authenticated using (true);
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_results'
      and policyname = 'eval_results_select_authenticated'
  ) then
    create policy eval_results_select_authenticated
      on public.eval_results for select to authenticated using (true);
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_runs'
      and policyname = 'eval_runs_insert_authenticated'
  ) then
    create policy eval_runs_insert_authenticated
      on public.eval_runs for insert to authenticated with check (true);
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_results'
      and policyname = 'eval_results_insert_authenticated'
  ) then
    create policy eval_results_insert_authenticated
      on public.eval_results for insert to authenticated with check (true);
  end if;
end
$restore_legacy_insert_policies$;

commit;
