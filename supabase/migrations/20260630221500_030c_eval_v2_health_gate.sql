-- CRAVE deploy migration: 20260630221500_030c_eval_v2_health_gate
-- Semantic source ID: CRAVE-030C / R05-A39 / BLK-007 prerequisite
-- Project: bdttccztjtrcaztjgkot
--
-- KHÔNG tự apply. Migration này chỉ được apply sau exact dry-run/change-set
-- approval. Không seed dataset, retrieval profile, eval run hoặc health metric.

begin;

do $preflight$
declare
  required_table text;
  target_table text;
  target_column text;
  marker text;
begin
  foreach required_table in array array[
    'user_profiles',
    'golden_questions',
    'eval_runs',
    'eval_results',
    'retrieval_profiles',
    'retrieval_log',
    'ai_queries',
    'system_health_metrics'
  ] loop
    if to_regclass(format('public.%I', required_table)) is null then
      raise exception 'CRAVE-030C: thiếu bảng bắt buộc public.%.', required_table;
    end if;
  end loop;

  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-030C: thiếu user_has_any_role(user_role_name[]).';
  end if;
  if to_regprocedure('public.crave_block_append_only_mutation()') is null then
    raise exception 'CRAVE-030C: thiếu crave_block_append_only_mutation().';
  end if;
  if to_regprocedure('gen_random_uuid()') is null then
    raise exception 'CRAVE-030C: thiếu gen_random_uuid().';
  end if;

  if exists (
    select 1
    from public.eval_results
    where run_id is not null and question_id is not null
    group by run_id, question_id
    having count(*) > 1
  ) then
    raise exception
      'CRAVE-030C: legacy eval_results có duplicate run/question; cần reconciliation trước unique lineage gate.';
  end if;

  foreach target_table in array array['eval_datasets', 'eval_failures'] loop
    if to_regclass(format('public.%I', target_table)) is not null then
      marker := coalesce(
        obj_description(to_regclass(format('public.%I', target_table)), 'pg_class'),
        ''
      );
      if marker not like 'CRAVE-030C:%' then
        raise exception
          'CRAVE-030C: public.% tồn tại nhưng không có marker tương thích.',
          target_table;
      end if;
    end if;
  end loop;

  foreach target_column in array array[
    'eval_contract_version',
    'dataset_id',
    'retrieval_profile_id',
    'workflow_name',
    'workflow_version',
    'git_commit_sha',
    'release_candidate',
    'run_status',
    'started_at',
    'completed_at',
    'parameters'
  ] loop
    if exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'eval_runs'
        and column_name = target_column
    ) then
      marker := coalesce(col_description(
        'public.eval_runs'::regclass,
        (select attnum from pg_attribute
         where attrelid = 'public.eval_runs'::regclass
           and attname = target_column
           and not attisdropped)
      ), '');
      if marker not like 'CRAVE-030C:%' then
        raise exception
          'CRAVE-030C: eval_runs.% tồn tại nhưng không có marker tương thích.',
          target_column;
      end if;
    end if;
  end loop;

  foreach target_column in array array[
    'retrieval_log_id',
    'ai_query_id',
    'permission_leakage_count',
    'stale_version_count',
    'citation_grounding_score',
    'permission_pass',
    'version_freshness_pass',
    'tool_policy_pass',
    'latency_ms',
    'evaluation_summary'
  ] loop
    if exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'eval_results'
        and column_name = target_column
    ) then
      marker := coalesce(col_description(
        'public.eval_results'::regclass,
        (select attnum from pg_attribute
         where attrelid = 'public.eval_results'::regclass
           and attname = target_column
           and not attisdropped)
      ), '');
      if marker not like 'CRAVE-030C:%' then
        raise exception
          'CRAVE-030C: eval_results.% tồn tại nhưng không có marker tương thích.',
          target_column;
      end if;
    end if;
  end loop;
end
$preflight$;

create table if not exists public.eval_datasets (
  id uuid primary key default gen_random_uuid(),
  dataset_name text not null check (dataset_name ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  dataset_version text not null check (dataset_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  artifact_path text not null,
  artifact_sha256 text not null check (artifact_sha256 ~ '^[0-9a-f]{64}$'),
  question_count integer not null check (question_count > 0),
  status text not null check (status in ('draft', 'approved', 'retired')),
  created_by uuid not null references public.user_profiles(id) on update restrict on delete restrict,
  approved_by uuid references public.user_profiles(id) on update restrict on delete restrict,
  approved_at timestamptz,
  valid_from timestamptz,
  expires_at timestamptz,
  retired_at timestamptz,
  created_at timestamptz not null default now(),
  constraint eval_datasets_name_version_key unique (dataset_name, dataset_version),
  constraint eval_datasets_artifact_path_check check (
    artifact_path ~ '^eval/datasets/[A-Za-z0-9_./-]+[.]jsonl$'
    and position('..' in artifact_path) = 0
  ),
  constraint eval_datasets_approval_check check (
    status <> 'approved'
    or (
      approved_by is not null
      and approved_by is distinct from created_by
      and approved_at is not null
      and valid_from is not null
      and (expires_at is null or expires_at > valid_from)
    )
  ),
  constraint eval_datasets_retired_check check (
    status <> 'retired' or retired_at is not null
  )
);

comment on table public.eval_datasets is
  'CRAVE-030C: immutable versioned eval dataset identity; migration never seeds or approves a dataset.';

alter table public.eval_runs
  add column if not exists eval_contract_version text not null default 'v1',
  add column if not exists dataset_id uuid,
  add column if not exists retrieval_profile_id uuid,
  add column if not exists workflow_name text,
  add column if not exists workflow_version text,
  add column if not exists git_commit_sha text,
  add column if not exists release_candidate text,
  add column if not exists run_status text not null default 'legacy_completed',
  add column if not exists started_at timestamptz,
  add column if not exists completed_at timestamptz,
  add column if not exists parameters jsonb not null default '{}'::jsonb;

comment on column public.eval_runs.eval_contract_version is
  'CRAVE-030C: v1 preserves legacy rows; only v2 participates in the controlled agent release gate.';
comment on column public.eval_runs.dataset_id is
  'CRAVE-030C: immutable approved eval dataset used by a v2 run.';
comment on column public.eval_runs.retrieval_profile_id is
  'CRAVE-030C: approved/effective retrieval profile replayed by a v2 run.';
comment on column public.eval_runs.workflow_name is
  'CRAVE-030C: controlled TKTL workflow name evaluated by a v2 run.';
comment on column public.eval_runs.workflow_version is
  'CRAVE-030C: immutable workflow source/live version evaluated by a v2 run.';
comment on column public.eval_runs.git_commit_sha is
  'CRAVE-030C: exact 40-hex source commit for reproducible v2 evidence.';
comment on column public.eval_runs.release_candidate is
  'CRAVE-030C: bounded release-candidate label evaluated by a v2 run.';
comment on column public.eval_runs.run_status is
  'CRAVE-030C: immutable final run disposition; legacy rows remain legacy_completed.';
comment on column public.eval_runs.started_at is
  'CRAVE-030C: v2 evaluation start timestamp.';
comment on column public.eval_runs.completed_at is
  'CRAVE-030C: v2 evaluation completion timestamp.';
comment on column public.eval_runs.parameters is
  'CRAVE-030C: bounded non-secret deterministic evaluation parameters.';

do $eval_run_constraints$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_runs'::regclass
      and conname = 'eval_runs_dataset_id_fkey'
  ) then
    alter table public.eval_runs
      add constraint eval_runs_dataset_id_fkey
      foreign key (dataset_id) references public.eval_datasets(id)
      on update restrict on delete restrict;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_runs'::regclass
      and conname = 'eval_runs_retrieval_profile_id_fkey'
  ) then
    alter table public.eval_runs
      add constraint eval_runs_retrieval_profile_id_fkey
      foreign key (retrieval_profile_id) references public.retrieval_profiles(id)
      on update restrict on delete restrict;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_runs'::regclass
      and conname = 'eval_runs_contract_version_check'
  ) then
    alter table public.eval_runs
      add constraint eval_runs_contract_version_check
      check (eval_contract_version in ('v1', 'v2'));
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_runs'::regclass
      and conname = 'eval_runs_status_check'
  ) then
    alter table public.eval_runs
      add constraint eval_runs_status_check
      check (run_status in ('legacy_completed', 'passed', 'failed', 'blocked'));
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_runs'::regclass
      and conname = 'eval_runs_parameters_check'
  ) then
    alter table public.eval_runs
      add constraint eval_runs_parameters_check
      check (
        jsonb_typeof(parameters) = 'object'
        and octet_length(parameters::text) <= 8192
      );
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_runs'::regclass
      and conname = 'eval_runs_v2_lineage_check'
  ) then
    alter table public.eval_runs
      add constraint eval_runs_v2_lineage_check
      check (
        eval_contract_version <> 'v2'
        or (
          dataset_id is not null
          and retrieval_profile_id is not null
          and workflow_name like 'TKTL%'
          and nullif(trim(workflow_version), '') is not null
          and git_commit_sha ~ '^[0-9a-f]{40}$'
          and release_candidate ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'
          and run_status in ('passed', 'failed', 'blocked')
          and started_at is not null
          and completed_at is not null
          and completed_at >= started_at
          and n_questions is not null
          and n_questions > 0
          and (
            (run_status = 'passed' and passed is true)
            or (run_status in ('failed', 'blocked') and passed is false)
          )
        )
      );
  end if;
end
$eval_run_constraints$;

alter table public.eval_results
  add column if not exists retrieval_log_id uuid,
  add column if not exists ai_query_id uuid,
  add column if not exists permission_leakage_count integer,
  add column if not exists stale_version_count integer,
  add column if not exists citation_grounding_score numeric,
  add column if not exists permission_pass boolean,
  add column if not exists version_freshness_pass boolean,
  add column if not exists tool_policy_pass boolean,
  add column if not exists latency_ms integer,
  add column if not exists evaluation_summary jsonb;

comment on column public.eval_results.retrieval_log_id is
  'CRAVE-030C: retrieval evidence evaluated by this v2 result.';
comment on column public.eval_results.ai_query_id is
  'CRAVE-030C: AI query/citation evidence evaluated by this v2 result.';
comment on column public.eval_results.permission_leakage_count is
  'CRAVE-030C: count of unauthorized source/result exposures; v2 PASS requires zero.';
comment on column public.eval_results.stale_version_count is
  'CRAVE-030C: count of stale/non-current versions returned; v2 PASS requires zero.';
comment on column public.eval_results.citation_grounding_score is
  'CRAVE-030C: normalized 0..1 grounded citation score.';
comment on column public.eval_results.permission_pass is
  'CRAVE-030C: explicit permission-isolation assertion.';
comment on column public.eval_results.version_freshness_pass is
  'CRAVE-030C: explicit current immutable-version assertion.';
comment on column public.eval_results.tool_policy_pass is
  'CRAVE-030C: explicit allowlisted-tool policy assertion.';
comment on column public.eval_results.latency_ms is
  'CRAVE-030C: non-negative measured end-to-end result latency.';
comment on column public.eval_results.evaluation_summary is
  'CRAVE-030C: bounded non-secret normalized assertion summary.';

do $eval_result_constraints$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_results'::regclass
      and conname = 'eval_results_retrieval_log_id_fkey'
  ) then
    alter table public.eval_results
      add constraint eval_results_retrieval_log_id_fkey
      foreign key (retrieval_log_id) references public.retrieval_log(id)
      on update restrict on delete restrict;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_results'::regclass
      and conname = 'eval_results_ai_query_id_fkey'
  ) then
    alter table public.eval_results
      add constraint eval_results_ai_query_id_fkey
      foreign key (ai_query_id) references public.ai_queries(id)
      on update restrict on delete restrict;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.eval_results'::regclass
      and conname = 'eval_results_v2_metric_ranges_check'
  ) then
    alter table public.eval_results
      add constraint eval_results_v2_metric_ranges_check
      check (
        (permission_leakage_count is null or permission_leakage_count >= 0)
        and (stale_version_count is null or stale_version_count >= 0)
        and (citation_grounding_score is null or citation_grounding_score between 0 and 1)
        and (latency_ms is null or latency_ms >= 0)
        and (
          evaluation_summary is null
          or (
            jsonb_typeof(evaluation_summary) = 'object'
            and octet_length(evaluation_summary::text) <= 8192
          )
        )
      );
  end if;
end
$eval_result_constraints$;

create table if not exists public.eval_failures (
  id uuid primary key default gen_random_uuid(),
  eval_result_id uuid not null references public.eval_results(id) on update restrict on delete restrict,
  failure_type text not null check (failure_type in (
    'retrieval_miss',
    'citation_grounding',
    'permission_leakage',
    'version_freshness',
    'tool_policy',
    'health_assertion',
    'other'
  )),
  severity text not null check (severity in ('critical', 'high', 'medium', 'low')),
  disposition text not null default 'open' check (disposition in ('open', 'waived')),
  owner_id uuid references public.user_profiles(id) on update restrict on delete restrict,
  created_by uuid not null references public.user_profiles(id) on update restrict on delete restrict,
  details jsonb not null default '{}'::jsonb,
  waiver_reason text,
  waiver_approved_by uuid references public.user_profiles(id) on update restrict on delete restrict,
  waiver_approved_at timestamptz,
  created_at timestamptz not null default now(),
  constraint eval_failures_result_type_key unique (eval_result_id, failure_type),
  constraint eval_failures_details_check check (
    jsonb_typeof(details) = 'object'
    and octet_length(details::text) <= 8192
  ),
  constraint eval_failures_waiver_check check (
    disposition <> 'waived'
    or (
      severity <> 'critical'
      and nullif(trim(waiver_reason), '') is not null
      and waiver_approved_by is not null
      and waiver_approved_by is distinct from created_by
      and waiver_approved_at is not null
    )
  )
);

comment on table public.eval_failures is
  'CRAVE-030C: append-only normalized v2 release-gate failures; rerun creates new evidence instead of overwriting history.';

create or replace function public.crave_validate_eval_run_v2_context()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $function$
declare
  dataset_row public.eval_datasets%rowtype;
  profile_row public.retrieval_profiles%rowtype;
begin
  if new.eval_contract_version <> 'v2' then
    return new;
  end if;

  select * into dataset_row
  from public.eval_datasets
  where id = new.dataset_id;

  if not found
    or dataset_row.status <> 'approved'
    or dataset_row.approved_by is null
    or dataset_row.approved_at is null
    or dataset_row.valid_from is null
    or dataset_row.valid_from > new.started_at
    or (dataset_row.expires_at is not null and dataset_row.expires_at <= new.started_at)
  then
    raise exception 'CRAVE-030C: v2 eval run yêu cầu approved/effective dataset.';
  end if;

  if new.n_questions is distinct from dataset_row.question_count then
    raise exception 'CRAVE-030C: v2 eval run n_questions không khớp approved dataset.';
  end if;

  select * into profile_row
  from public.retrieval_profiles
  where id = new.retrieval_profile_id;

  if not found
    or profile_row.status <> 'approved'
    or profile_row.approved_by is null
    or profile_row.approved_at is null
    or profile_row.valid_from is null
    or profile_row.valid_from > new.started_at
    or (profile_row.expires_at is not null and profile_row.expires_at <= new.started_at)
  then
    raise exception 'CRAVE-030C: v2 eval run yêu cầu approved/effective retrieval profile.';
  end if;

  return new;
end
$function$;

create or replace function public.crave_validate_eval_result_v2_context()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $function$
declare
  contract_version text;
  retrieval_query_id uuid;
begin
  select eval_contract_version into contract_version
  from public.eval_runs
  where id = new.run_id;

  if contract_version is distinct from 'v2' then
    return new;
  end if;

  if new.retrieval_log_id is null
    or new.ai_query_id is null
    or new.question_id is null
    or new.permission_leakage_count is null
    or new.stale_version_count is null
    or new.citation_grounding_score is null
    or new.permission_pass is null
    or new.version_freshness_pass is null
    or new.tool_policy_pass is null
    or new.latency_ms is null
    or new.evaluation_summary is null
  then
    raise exception 'CRAVE-030C: v2 eval result thiếu normalized evidence bắt buộc.';
  end if;

  select query_id into retrieval_query_id
  from public.retrieval_log
  where id = new.retrieval_log_id;

  if retrieval_query_id is distinct from new.ai_query_id then
    raise exception 'CRAVE-030C: v2 eval result retrieval/query lineage không khớp.';
  end if;

  if new.passed is true and (
    new.permission_leakage_count <> 0
    or new.stale_version_count <> 0
    or new.permission_pass is not true
    or new.version_freshness_pass is not true
    or new.tool_policy_pass is not true
    or new.citation_grounding_score < 1
  ) then
    raise exception 'CRAVE-030C: v2 PASS không đạt permission/version/tool/citation assertions.';
  end if;

  return new;
end
$function$;

create or replace function public.crave_validate_eval_failure_context()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $function$
declare
  result_row public.eval_results%rowtype;
  contract_version text;
begin
  select * into result_row
  from public.eval_results
  where id = new.eval_result_id;

  select eval_contract_version into contract_version
  from public.eval_runs
  where id = result_row.run_id;

  if contract_version is distinct from 'v2' or result_row.passed is distinct from false then
    raise exception 'CRAVE-030C: eval_failure chỉ được gắn vào failed v2 eval result.';
  end if;

  if new.failure_type = 'permission_leakage'
    and not (
      result_row.permission_pass is false
      and result_row.permission_leakage_count > 0
    )
  then
    raise exception 'CRAVE-030C: permission_leakage failure thiếu leakage evidence.';
  end if;

  if new.failure_type = 'version_freshness'
    and not (
      result_row.version_freshness_pass is false
      and result_row.stale_version_count > 0
    )
  then
    raise exception 'CRAVE-030C: version_freshness failure thiếu stale-version evidence.';
  end if;

  if new.failure_type = 'tool_policy' and result_row.tool_policy_pass is not false then
    raise exception 'CRAVE-030C: tool_policy failure thiếu denied-tool evidence.';
  end if;

  if new.failure_type = 'citation_grounding'
    and not (result_row.citation_grounding_score < 1)
  then
    raise exception 'CRAVE-030C: citation_grounding failure thiếu grounding evidence.';
  end if;

  if new.failure_type = 'retrieval_miss'
    and coalesce((result_row.evaluation_summary->>'retrieval_miss')::boolean, false) is not true
  then
    raise exception 'CRAVE-030C: retrieval_miss failure thiếu normalized miss evidence.';
  end if;

  if new.failure_type = 'health_assertion' and not (new.details ? 'health_gate') then
    raise exception 'CRAVE-030C: health_assertion failure thiếu health_gate details.';
  end if;

  return new;
end
$function$;

create or replace function public.crave_evaluate_eval_v2_release_gate_v1(
  p_run_id uuid
) returns jsonb
language plpgsql
stable
security invoker
set search_path = public, pg_temp
as $function$
declare
  run_row public.eval_runs%rowtype;
  result_count integer;
  failed_result_count integer;
  untracked_failed_result_count integer;
  open_failure_count integer;
  critical_failure_count integer;
  permission_leakage_total bigint;
  stale_version_total bigint;
  citation_failure_count integer;
  permission_failure_count integer;
  version_failure_count integer;
  tool_failure_count integer;
begin
  select * into run_row
  from public.eval_runs
  where id = p_run_id;

  if not found or run_row.eval_contract_version <> 'v2' then
    raise exception 'CRAVE-030C: release gate yêu cầu existing v2 eval run.';
  end if;

  select
    count(*)::integer,
    count(*) filter (where result.passed is distinct from true)::integer,
    coalesce(sum(result.permission_leakage_count), 0)::bigint,
    coalesce(sum(result.stale_version_count), 0)::bigint,
    count(*) filter (where result.citation_grounding_score < 1)::integer,
    count(*) filter (where result.permission_pass is distinct from true)::integer,
    count(*) filter (where result.version_freshness_pass is distinct from true)::integer,
    count(*) filter (where result.tool_policy_pass is distinct from true)::integer
  into
    result_count,
    failed_result_count,
    permission_leakage_total,
    stale_version_total,
    citation_failure_count,
    permission_failure_count,
    version_failure_count,
    tool_failure_count
  from public.eval_results result
  where result.run_id = p_run_id;

  select count(*)::integer
  into untracked_failed_result_count
  from public.eval_results result
  where result.run_id = p_run_id
    and result.passed is distinct from true
    and not exists (
      select 1 from public.eval_failures failure
      where failure.eval_result_id = result.id
    );

  select
    count(*) filter (where failure.disposition = 'open')::integer,
    count(*) filter (where failure.severity = 'critical')::integer
  into open_failure_count, critical_failure_count
  from public.eval_failures failure
  join public.eval_results result on result.id = failure.eval_result_id
  where result.run_id = p_run_id;

  return jsonb_build_object(
    'gate', 'CRAVE_EVAL_V2_RELEASE_GATE_V1',
    'evaluated_at', now(),
    'run_id', run_row.id,
    'run_status', run_row.run_status,
    'expected_results', run_row.n_questions,
    'result_count', result_count,
    'failed_result_count', failed_result_count,
    'untracked_failed_result_count', untracked_failed_result_count,
    'open_failure_count', open_failure_count,
    'critical_failure_count', critical_failure_count,
    'permission_leakage_total', permission_leakage_total,
    'stale_version_total', stale_version_total,
    'citation_failure_count', citation_failure_count,
    'permission_failure_count', permission_failure_count,
    'version_failure_count', version_failure_count,
    'tool_failure_count', tool_failure_count,
    'passed',
      run_row.run_status = 'passed'
      and run_row.passed is true
      and result_count = run_row.n_questions
      and failed_result_count = 0
      and untracked_failed_result_count = 0
      and open_failure_count = 0
      and critical_failure_count = 0
      and permission_leakage_total = 0
      and stale_version_total = 0
      and citation_failure_count = 0
      and permission_failure_count = 0
      and version_failure_count = 0
      and tool_failure_count = 0
  );
end
$function$;

create or replace function public.crave_evaluate_system_health_gate_v1(
  p_required_metrics text[],
  p_freshness interval default interval '15 minutes'
) returns jsonb
language plpgsql
stable
security invoker
set search_path = public, pg_temp
as $function$
declare
  required_metrics text[];
  missing_metrics text[];
  unhealthy_metrics text[];
  observed_count integer;
begin
  select array_agg(distinct metric_name order by metric_name)
  into required_metrics
  from unnest(p_required_metrics) as required(metric_name);

  if required_metrics is null
    or cardinality(required_metrics) = 0
    or cardinality(required_metrics) > 32
    or exists (
      select 1 from unnest(required_metrics) metric(metric_name)
      where metric_name is null
        or metric_name !~ '^[a-z][a-z0-9_.-]{2,127}$'
    )
  then
    raise exception 'CRAVE-030C: required metric list phải có 1..32 metric names hợp lệ.';
  end if;

  if p_freshness is null
    or p_freshness < interval '1 minute'
    or p_freshness > interval '24 hours'
  then
    raise exception 'CRAVE-030C: freshness window phải trong 1 phút..24 giờ.';
  end if;

  with latest as (
    select distinct on (metric_name)
      metric_name,
      status,
      measured_at
    from public.system_health_metrics
    where metric_name = any(required_metrics)
      and measured_at >= now() - p_freshness
    order by metric_name, measured_at desc, created_at desc, id desc
  )
  select
    coalesce(array_agg(metric.metric_name order by metric.metric_name)
      filter (where latest.metric_name is null), '{}'::text[]),
    coalesce(array_agg(metric.metric_name order by metric.metric_name)
      filter (where latest.metric_name is not null and latest.status <> 'healthy'), '{}'::text[]),
    count(latest.metric_name)::integer
  into missing_metrics, unhealthy_metrics, observed_count
  from unnest(required_metrics) metric(metric_name)
  left join latest using (metric_name);

  return jsonb_build_object(
    'gate', 'CRAVE_SYSTEM_HEALTH_GATE_V1',
    'evaluated_at', now(),
    'freshness_seconds', extract(epoch from p_freshness)::integer,
    'required_metrics', required_metrics,
    'required_count', cardinality(required_metrics),
    'observed_count', observed_count,
    'missing_metrics', missing_metrics,
    'unhealthy_metrics', unhealthy_metrics,
    'passed', cardinality(missing_metrics) = 0 and cardinality(unhealthy_metrics) = 0
  );
end
$function$;

drop trigger if exists eval_runs_validate_v2_context on public.eval_runs;
create trigger eval_runs_validate_v2_context
before insert or update on public.eval_runs
for each row execute function public.crave_validate_eval_run_v2_context();

drop trigger if exists eval_results_validate_v2_context on public.eval_results;
create trigger eval_results_validate_v2_context
before insert or update on public.eval_results
for each row execute function public.crave_validate_eval_result_v2_context();

drop trigger if exists eval_failures_validate_context on public.eval_failures;
create trigger eval_failures_validate_context
before insert or update on public.eval_failures
for each row execute function public.crave_validate_eval_failure_context();

create index if not exists idx_eval_datasets_status_version
  on public.eval_datasets (status, dataset_name, dataset_version);
create index if not exists idx_eval_runs_v2_dataset
  on public.eval_runs (dataset_id, run_at desc)
  where eval_contract_version = 'v2';
create index if not exists idx_eval_runs_v2_profile
  on public.eval_runs (retrieval_profile_id, run_at desc)
  where eval_contract_version = 'v2';
create index if not exists idx_eval_results_retrieval_log
  on public.eval_results (retrieval_log_id)
  where retrieval_log_id is not null;
create index if not exists idx_eval_results_ai_query
  on public.eval_results (ai_query_id)
  where ai_query_id is not null;
create unique index if not exists idx_eval_results_run_question_unique
  on public.eval_results (run_id, question_id)
  where run_id is not null and question_id is not null;
create index if not exists idx_eval_failures_open
  on public.eval_failures (severity, created_at desc)
  where disposition = 'open';

alter table public.eval_datasets enable row level security;
alter table public.eval_failures enable row level security;

revoke all on table public.eval_datasets, public.eval_failures
from public, anon, authenticated;
grant select on table public.eval_datasets, public.eval_failures to authenticated;
grant select, insert on table
  public.eval_datasets,
  public.eval_failures,
  public.eval_runs,
  public.eval_results
to service_role;

revoke insert, update, delete, truncate on table
  public.eval_runs,
  public.eval_results
from authenticated;

revoke execute on function public.run_fts_eval_v1(integer, text, text)
from authenticated;
grant execute on function public.run_fts_eval_v1(integer, text, text)
to service_role;

drop policy if exists eval_runs_insert_authenticated on public.eval_runs;
drop policy if exists eval_results_insert_authenticated on public.eval_results;
drop policy if exists eval_runs_select_authenticated on public.eval_runs;
drop policy if exists eval_results_select_authenticated on public.eval_results;

do $read_policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_runs'
      and policyname = 'eval_runs_read_auditor'
  ) then
    create policy eval_runs_read_auditor
      on public.eval_runs for select to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name,
        'auditor'::public.user_role_name
      ]));
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_results'
      and policyname = 'eval_results_read_auditor'
  ) then
    create policy eval_results_read_auditor
      on public.eval_results for select to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name,
        'auditor'::public.user_role_name
      ]));
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_datasets'
      and policyname = 'eval_datasets_read_auditor'
  ) then
    create policy eval_datasets_read_auditor
      on public.eval_datasets for select to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name,
        'auditor'::public.user_role_name
      ]));
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'eval_failures'
      and policyname = 'eval_failures_read_auditor'
  ) then
    create policy eval_failures_read_auditor
      on public.eval_failures for select to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name,
        'auditor'::public.user_role_name
      ]));
  end if;
end
$read_policies$;

do $append_only_triggers$
declare
  target_table text;
  trigger_name text;
begin
  foreach target_table in array array[
    'eval_datasets',
    'eval_runs',
    'eval_results',
    'eval_failures'
  ] loop
    trigger_name := target_table || '_append_only_guard';
    if not exists (
      select 1
      from pg_trigger trigger_row
      where trigger_row.tgrelid = format('public.%I', target_table)::regclass
        and trigger_row.tgname = trigger_name
        and not trigger_row.tgisinternal
    ) then
      execute format(
        'create trigger %I before update or delete or truncate on public.%I '
        || 'for each statement execute function public.crave_block_append_only_mutation()',
        trigger_name,
        target_table
      );
    end if;
  end loop;
end
$append_only_triggers$;

revoke all on function public.crave_evaluate_system_health_gate_v1(text[], interval)
from public, anon;
grant execute on function public.crave_evaluate_system_health_gate_v1(text[], interval)
to authenticated, service_role;

revoke all on function public.crave_evaluate_eval_v2_release_gate_v1(uuid)
from public, anon;
grant execute on function public.crave_evaluate_eval_v2_release_gate_v1(uuid)
to authenticated, service_role;

comment on function public.crave_evaluate_system_health_gate_v1(text[], interval) is
  'CRAVE-030C: SECURITY INVOKER fail-closed gate; PASS requires every required metric fresh and healthy.';
comment on function public.crave_evaluate_eval_v2_release_gate_v1(uuid) is
  'CRAVE-030C: SECURITY INVOKER v2 release assertion; PASS requires complete zero-failure normalized results.';

do $post_assert$
declare
  legacy_runs bigint;
  legacy_results bigint;
begin
  select count(*) into legacy_runs
  from public.eval_runs
  where eval_contract_version <> 'v1';

  if legacy_runs <> 0 then
    raise exception 'CRAVE-030C: migration không được tự nâng legacy eval_runs thành v2.';
  end if;

  select count(*) into legacy_results
  from public.eval_results result
  join public.eval_runs run on run.id = result.run_id
  where run.eval_contract_version <> 'v1';

  if legacy_results <> 0 then
    raise exception 'CRAVE-030C: migration không được tự nâng legacy eval_results thành v2.';
  end if;

  if exists (select 1 from public.eval_datasets)
    or exists (select 1 from public.eval_failures)
  then
    raise exception 'CRAVE-030C: migration không được seed dataset/failure evidence.';
  end if;
end
$post_assert$;

commit;
