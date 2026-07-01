-- CRAVE-030B catalog assertions. Run only after migration apply in a controlled gate.
-- Read-only assertions; no fixture writes.

do $catalog_test$
declare
  target_table text;
  missing_policies bigint;
  missing_append_triggers bigint;
begin
  foreach target_table in array array[
    'retrieval_profiles',
    'retrieval_log',
    'retrieval_candidates',
    'agent_sessions',
    'tool_call_log',
    'system_health_metrics'
  ] loop
    if to_regclass(format('public.%I', target_table)) is null then
      raise exception 'CRAVE-030B TEST: thiếu public.%.', target_table;
    end if;
    if not (
      select relrowsecurity
      from pg_class
      where oid = to_regclass(format('public.%I', target_table))
    ) then
      raise exception 'CRAVE-030B TEST: RLS chưa bật trên public.%.', target_table;
    end if;
  end loop;

  select count(*) into missing_policies
  from unnest(array[
    'retrieval_profiles_read_approved_or_auditor',
    'retrieval_log_read_own_or_auditor',
    'retrieval_candidates_read_own_or_auditor',
    'agent_sessions_read_own_or_auditor',
    'tool_call_log_read_own_or_auditor',
    'system_health_metrics_read_auditor'
  ]) expected(policy_name)
  where not exists (
    select 1 from pg_policies policy
    where policy.schemaname = 'public'
      and policy.policyname = expected.policy_name
  );

  select count(*) into missing_append_triggers
  from (values
    ('retrieval_log', 'retrieval_log_append_only_guard'),
    ('retrieval_candidates', 'retrieval_candidates_append_only_guard'),
    ('tool_call_log', 'tool_call_log_append_only_guard'),
    ('system_health_metrics', 'system_health_metrics_append_only_guard'),
    ('ai_query_sources', 'ai_query_sources_append_only_guard')
  ) expected(table_name, trigger_name)
  where not exists (
    select 1 from pg_trigger trigger_row
    where trigger_row.tgrelid = to_regclass(format('public.%I', expected.table_name))
      and trigger_row.tgname = expected.trigger_name
      and trigger_row.tgfoid = to_regprocedure('public.crave_block_append_only_mutation()')
  );

  if missing_policies <> 0 or missing_append_triggers <> 0 then
    raise exception 'CRAVE-030B TEST: missing_policies=% missing_append_triggers=%.',
      missing_policies, missing_append_triggers;
  end if;
  if to_regprocedure('public.crave_validate_ai_query_source_lineage()') is null then
    raise exception 'CRAVE-030B TEST: thiếu citation lineage validator.';
  end if;
  if to_regprocedure('public.crave_validate_retrieval_log_context()') is null
    or to_regprocedure('public.crave_validate_retrieval_candidate_lineage()') is null
  then
    raise exception 'CRAVE-030B TEST: thiếu retrieval context/lineage validators.';
  end if;
  if has_table_privilege('authenticated', 'public.retrieval_log', 'insert')
    or has_table_privilege('authenticated', 'public.tool_call_log', 'insert')
  then
    raise exception 'CRAVE-030B TEST: authenticated có broad evidence INSERT.';
  end if;
end
$catalog_test$;

select 'PASS_030B_AGENT_EVIDENCE_FOUNDATION_CATALOG' as result;
