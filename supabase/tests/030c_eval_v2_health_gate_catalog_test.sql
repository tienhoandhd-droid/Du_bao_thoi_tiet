-- CRAVE-030C catalog-only assertion test. No DML and no fixture rows.

do $catalog_test$
declare
  missing_count integer;
  function_row record;
begin
  if to_regclass('public.eval_datasets') is null
    or to_regclass('public.eval_failures') is null
  then
    raise exception 'CRAVE-030C catalog: thiếu eval_datasets/eval_failures.';
  end if;

  if not (
    select bool_and(class.relrowsecurity)
    from pg_class class
    where class.oid in (
      'public.eval_datasets'::regclass,
      'public.eval_failures'::regclass
    )
  ) then
    raise exception 'CRAVE-030C catalog: RLS chưa bật trên mọi bảng mới.';
  end if;

  select count(*) into missing_count
  from (values
    ('eval_runs', 'eval_runs_read_auditor'),
    ('eval_results', 'eval_results_read_auditor'),
    ('eval_datasets', 'eval_datasets_read_auditor'),
    ('eval_failures', 'eval_failures_read_auditor')
  ) expected(table_name, policy_name)
  left join pg_policies policy_row
    on policy_row.schemaname = 'public'
   and policy_row.tablename = expected.table_name
   and policy_row.policyname = expected.policy_name
  where policy_row.policyname is null;

  if missing_count <> 0 then
    raise exception 'CRAVE-030C catalog: thiếu % read policies.', missing_count;
  end if;

  if exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and (
        (tablename = 'eval_runs' and policyname = 'eval_runs_select_authenticated')
        or (tablename = 'eval_results' and policyname = 'eval_results_select_authenticated')
      )
  ) then
    raise exception 'CRAVE-030C catalog: legacy broad authenticated eval SELECT policy còn tồn tại.';
  end if;

  select count(*) into missing_count
  from (values
    ('eval_datasets', 'eval_datasets_append_only_guard'),
    ('eval_runs', 'eval_runs_append_only_guard'),
    ('eval_results', 'eval_results_append_only_guard'),
    ('eval_failures', 'eval_failures_append_only_guard'),
    ('eval_runs', 'eval_runs_validate_v2_context'),
    ('eval_results', 'eval_results_validate_v2_context'),
    ('eval_failures', 'eval_failures_validate_context')
  ) expected(table_name, trigger_name)
  left join pg_trigger trigger_row
    on trigger_row.tgrelid = format('public.%I', expected.table_name)::regclass
   and trigger_row.tgname = expected.trigger_name
   and not trigger_row.tgisinternal
  where trigger_row.oid is null;

  if missing_count <> 0 then
    raise exception 'CRAVE-030C catalog: thiếu % validation/append triggers.', missing_count;
  end if;

  if has_table_privilege('authenticated', 'public.eval_runs', 'INSERT')
    or has_table_privilege('authenticated', 'public.eval_results', 'INSERT')
    or has_table_privilege('authenticated', 'public.eval_datasets', 'INSERT')
    or has_table_privilege('authenticated', 'public.eval_failures', 'INSERT')
    or has_function_privilege(
      'authenticated',
      'public.run_fts_eval_v1(integer,text,text)',
      'EXECUTE'
    )
  then
    raise exception 'CRAVE-030C catalog: authenticated có broad eval evidence write path.';
  end if;

  if not (
    has_table_privilege('service_role', 'public.eval_runs', 'INSERT')
    and has_table_privilege('service_role', 'public.eval_results', 'INSERT')
    and has_table_privilege('service_role', 'public.eval_datasets', 'INSERT')
    and has_table_privilege('service_role', 'public.eval_failures', 'INSERT')
    and has_function_privilege(
      'service_role',
      'public.run_fts_eval_v1(integer,text,text)',
      'EXECUTE'
    )
  ) then
    raise exception 'CRAVE-030C catalog: controlled backend INSERT path chưa đủ.';
  end if;

  if to_regprocedure('public.crave_validate_eval_run_v2_context()') is null
    or to_regprocedure('public.crave_validate_eval_result_v2_context()') is null
    or to_regprocedure('public.crave_validate_eval_failure_context()') is null
  then
    raise exception 'CRAVE-030C catalog: thiếu v2 context validators.';
  end if;

  if to_regclass('public.idx_eval_results_run_question_unique') is null then
    raise exception 'CRAVE-030C catalog: thiếu unique run/question result lineage index.';
  end if;

  if to_regprocedure('public.crave_evaluate_eval_v2_release_gate_v1(uuid)') is null then
    raise exception 'CRAVE-030C catalog: thiếu eval-v2 release gate.';
  end if;

  if exists (
    select 1 from pg_proc procedure
    where procedure.oid = to_regprocedure(
      'public.crave_evaluate_eval_v2_release_gate_v1(uuid)'
    )
      and (
        procedure.prosecdef
        or procedure.provolatile <> 's'
        or not ('search_path=public, pg_temp' = any(procedure.proconfig))
      )
  ) then
    raise exception 'CRAVE-030C catalog: eval-v2 gate không phải stable SECURITY INVOKER fixed-search-path.';
  end if;

  select procedure.prosecdef, procedure.provolatile, procedure.proconfig
  into function_row
  from pg_proc procedure
  where procedure.oid = to_regprocedure(
    'public.crave_evaluate_system_health_gate_v1(text[],interval)'
  );

  if not found
    or function_row.prosecdef
    or function_row.provolatile <> 's'
    or not ('search_path=public, pg_temp' = any(function_row.proconfig))
  then
    raise exception 'CRAVE-030C catalog: health gate không phải stable SECURITY INVOKER fixed-search-path.';
  end if;

  if exists (select 1 from public.eval_datasets)
    or exists (select 1 from public.eval_failures)
    or exists (
      select 1 from public.eval_runs where eval_contract_version = 'v2'
    )
  then
    raise exception 'CRAVE-030C catalog: migration đã seed hoặc relabel v2 evidence.';
  end if;
end
$catalog_test$;

select 'PASS_030C_EVAL_V2_HEALTH_GATE_CATALOG' as result;
