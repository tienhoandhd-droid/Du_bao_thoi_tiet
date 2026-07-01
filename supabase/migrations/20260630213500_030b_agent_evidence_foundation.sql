-- CRAVE deploy migration: 20260630213500_030b_agent_evidence_foundation
-- Semantic source ID: CRAVE-030B / R05-A38 / BLK-007 prerequisite
-- Project: bdttccztjtrcaztjgkot
--
-- KHÔNG tự apply. Migration này tạo evidence foundation cho controlled agent.
-- Chỉ apply sau exact dry-run/change set/approval riêng.

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
    'document_versions',
    'document_chunks',
    'ai_queries',
    'ai_query_sources',
    'workflow_runs',
    'audit_log'
  ] loop
    if to_regclass(format('public.%I', required_table)) is null then
      raise exception 'CRAVE-030B: thiếu bảng bắt buộc public.%.', required_table;
    end if;
  end loop;

  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-030B: thiếu user_has_any_role(user_role_name[]).';
  end if;
  if to_regprocedure('public.crave_block_append_only_mutation()') is null then
    raise exception 'CRAVE-030B: thiếu crave_block_append_only_mutation().';
  end if;
  if to_regprocedure('public.crave_validate_document_chunk_version_lineage()') is null then
    raise exception 'CRAVE-030B: thiếu CRAVE-030 chunk-version lineage validator.';
  end if;
  if to_regprocedure('gen_random_uuid()') is null then
    raise exception 'CRAVE-030B: thiếu gen_random_uuid().';
  end if;

  if exists (select 1 from public.ai_query_sources) then
    raise exception
      'CRAVE-030B: ai_query_sources không rỗng; cần reconciliation riêng, không tự gắn verified evidence hồi tố.';
  end if;

  foreach target_table in array array[
    'retrieval_profiles',
    'retrieval_log',
    'retrieval_candidates',
    'agent_sessions',
    'tool_call_log',
    'system_health_metrics'
  ] loop
    if to_regclass(format('public.%I', target_table)) is not null then
      marker := coalesce(obj_description(to_regclass(format('public.%I', target_table)), 'pg_class'), '');
      if marker not like 'CRAVE-030B:%' then
        raise exception 'CRAVE-030B: public.% tồn tại nhưng không có marker tương thích.', target_table;
      end if;
    end if;
  end loop;

  foreach target_column in array array[
    'query_normalized',
    'query_expanded',
    'retrieval_profile_version',
    'search_mode',
    'no_source_reason',
    'generation_skipped'
  ] loop
    if exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'ai_queries'
        and column_name = target_column
    ) then
      marker := coalesce(col_description(
        'public.ai_queries'::regclass,
        (select attnum from pg_attribute
         where attrelid = 'public.ai_queries'::regclass
           and attname = target_column
           and not attisdropped)
      ), '');
      if marker not like 'CRAVE-030B:%' then
        raise exception 'CRAVE-030B: ai_queries.% tồn tại nhưng không có marker tương thích.', target_column;
      end if;
    end if;
  end loop;

  foreach target_column in array array[
    'document_version_id',
    'retrieval_candidate_id',
    'final_score',
    'citation_verified_at'
  ] loop
    if exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'ai_query_sources'
        and column_name = target_column
    ) then
      marker := coalesce(col_description(
        'public.ai_query_sources'::regclass,
        (select attnum from pg_attribute
         where attrelid = 'public.ai_query_sources'::regclass
           and attname = target_column
           and not attisdropped)
      ), '');
      if marker not like 'CRAVE-030B:%' then
        raise exception 'CRAVE-030B: ai_query_sources.% tồn tại nhưng không có marker tương thích.', target_column;
      end if;
    end if;
  end loop;
end
$preflight$;

create table if not exists public.retrieval_profiles (
  id uuid primary key default gen_random_uuid(),
  profile_name text not null,
  profile_version text not null,
  embedding_model text not null,
  embedding_dimensions integer not null check (embedding_dimensions = 1536),
  fts_pool_size integer not null check (fts_pool_size between 1 and 200),
  vector_pool_size integer not null check (vector_pool_size between 1 and 200),
  final_top_k integer not null check (final_top_k between 1 and 50),
  rrf_k integer not null default 60 check (rrf_k > 0),
  score_threshold numeric check (score_threshold is null or score_threshold between 0 and 1),
  weights jsonb not null default '{}'::jsonb,
  status text not null default 'draft' check (status in ('draft', 'approved', 'retired')),
  git_commit text,
  approved_by uuid references public.user_profiles(id) on update restrict on delete restrict,
  approved_at timestamptz,
  valid_from timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  constraint retrieval_profiles_name_version_key unique (profile_name, profile_version),
  constraint retrieval_profiles_approval_check check (
    status <> 'approved'
    or (
      approved_by is not null
      and approved_at is not null
      and valid_from is not null
      and (expires_at is null or expires_at > valid_from)
    )
  )
);

comment on table public.retrieval_profiles is
  'CRAVE-030B: versioned retrieval configuration; no profile is auto-approved by migration.';

alter table public.ai_queries
  add column if not exists query_normalized text,
  add column if not exists query_expanded text,
  add column if not exists retrieval_profile_version text,
  add column if not exists search_mode text,
  add column if not exists no_source_reason text,
  add column if not exists generation_skipped boolean not null default false;

comment on column public.ai_queries.query_normalized is
  'CRAVE-030B: deterministic normalized query used for retrieval replay.';
comment on column public.ai_queries.query_expanded is
  'CRAVE-030B: approved/fallback expanded query used for retrieval replay.';
comment on column public.ai_queries.retrieval_profile_version is
  'CRAVE-030B: immutable profile version label captured by the query.';
comment on column public.ai_queries.search_mode is
  'CRAVE-030B: hybrid, fts_only, vector_only or no_source runtime disposition.';
comment on column public.ai_queries.no_source_reason is
  'CRAVE-030B: fail-closed reason when generation has no permitted source.';
comment on column public.ai_queries.generation_skipped is
  'CRAVE-030B: true when answer generation was intentionally skipped.';

do $ai_query_checks$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_queries'::regclass
      and conname = 'ai_queries_search_mode_check'
  ) then
    alter table public.ai_queries
      add constraint ai_queries_search_mode_check
      check (search_mode is null or search_mode in ('hybrid', 'fts_only', 'vector_only', 'no_source'));
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_queries'::regclass
      and conname = 'ai_queries_no_source_check'
  ) then
    alter table public.ai_queries
      add constraint ai_queries_no_source_check
      check (
        search_mode is distinct from 'no_source'
        or (generation_skipped = true and nullif(trim(no_source_reason), '') is not null)
      );
  end if;
end
$ai_query_checks$;

create table if not exists public.retrieval_log (
  id uuid primary key default gen_random_uuid(),
  query_id uuid not null references public.ai_queries(id) on update restrict on delete restrict,
  user_id uuid not null references public.user_profiles(id) on update restrict on delete restrict,
  profile_id uuid not null references public.retrieval_profiles(id) on update restrict on delete restrict,
  workflow_name text not null,
  workflow_version text not null,
  search_mode text not null check (search_mode in ('hybrid', 'fts_only', 'vector_only', 'no_source')),
  filters jsonb not null default '{}'::jsonb,
  fts_candidate_count integer not null default 0 check (fts_candidate_count >= 0),
  vector_candidate_count integer not null default 0 check (vector_candidate_count >= 0),
  selected_count integer not null default 0 check (selected_count >= 0),
  no_source_reason text,
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  created_at timestamptz not null default now(),
  constraint retrieval_log_no_source_check check (
    search_mode <> 'no_source'
    or (selected_count = 0 and nullif(trim(no_source_reason), '') is not null)
  )
);

comment on table public.retrieval_log is
  'CRAVE-030B: append-only retrieval run evidence correlated to one AI query and approved profile.';

create table if not exists public.retrieval_candidates (
  id uuid primary key default gen_random_uuid(),
  retrieval_log_id uuid not null references public.retrieval_log(id) on update restrict on delete restrict,
  chunk_id uuid not null references public.document_chunks(id) on update restrict on delete restrict,
  document_version_id uuid not null references public.document_versions(id) on update restrict on delete restrict,
  fts_rank integer check (fts_rank is null or fts_rank > 0),
  vector_rank integer check (vector_rank is null or vector_rank > 0),
  fts_score double precision,
  vector_score double precision,
  rrf_score double precision not null,
  metadata_boost double precision not null default 0,
  final_score double precision not null,
  final_rank integer check (final_rank is null or final_rank > 0),
  selected boolean not null default false,
  rejection_reason text,
  created_at timestamptz not null default now(),
  constraint retrieval_candidates_unique unique (retrieval_log_id, chunk_id),
  constraint retrieval_candidates_selected_rank_check check (not selected or final_rank is not null)
);

comment on table public.retrieval_candidates is
  'CRAVE-030B: append-only candidate scores/ranks and selected disposition with immutable chunk-version lineage.';

create or replace function public.crave_validate_retrieval_log_context()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $function$
declare
  query_user_id uuid;
  profile_status text;
  profile_valid_from timestamptz;
  profile_expires_at timestamptz;
begin
  select query_row.user_id
  into query_user_id
  from public.ai_queries query_row
  where query_row.id = new.query_id;

  if not found or query_user_id is distinct from new.user_id then
    raise exception 'CRAVE-030B: retrieval log user không khớp AI query owner.';
  end if;

  select profile.status, profile.valid_from, profile.expires_at
  into profile_status, profile_valid_from, profile_expires_at
  from public.retrieval_profiles profile
  where profile.id = new.profile_id;

  if not found
    or profile_status <> 'approved'
    or profile_valid_from is null
    or profile_valid_from > new.created_at
    or (profile_expires_at is not null and profile_expires_at <= new.created_at)
  then
    raise exception 'CRAVE-030B: retrieval log phải dùng approved/effective profile.';
  end if;
  return new;
end
$function$;

comment on function public.crave_validate_retrieval_log_context() is
  'CRAVE-030B: retrieval run user must own query and profile must be approved/effective at run time.';

create or replace function public.crave_validate_retrieval_candidate_lineage()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $function$
declare
  chunk_version_id uuid;
begin
  select chunk.document_version_id
  into chunk_version_id
  from public.document_chunks chunk
  where chunk.id = new.chunk_id;

  if not found or chunk_version_id is distinct from new.document_version_id then
    raise exception 'CRAVE-030B: retrieval candidate chunk/version lineage không khớp.';
  end if;
  if new.selected and new.final_rank is null then
    raise exception 'CRAVE-030B: selected retrieval candidate phải có final_rank.';
  end if;
  return new;
end
$function$;

comment on function public.crave_validate_retrieval_candidate_lineage() is
  'CRAVE-030B: candidate must preserve exact chunk/document_version_id lineage.';

do $retrieval_triggers$
begin
  if not exists (
    select 1 from pg_trigger
    where tgrelid = 'public.retrieval_log'::regclass
      and tgname = 'retrieval_log_validate_context'
  ) then
    create trigger retrieval_log_validate_context
      before insert on public.retrieval_log
      for each row execute function public.crave_validate_retrieval_log_context();
  end if;
  if not exists (
    select 1 from pg_trigger
    where tgrelid = 'public.retrieval_candidates'::regclass
      and tgname = 'retrieval_candidates_validate_lineage'
  ) then
    create trigger retrieval_candidates_validate_lineage
      before insert on public.retrieval_candidates
      for each row execute function public.crave_validate_retrieval_candidate_lineage();
  end if;
end
$retrieval_triggers$;

create table if not exists public.agent_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.user_profiles(id) on update restrict on delete restrict,
  owner_id uuid not null references public.user_profiles(id) on update restrict on delete restrict,
  purpose text not null,
  policy_name text not null,
  policy_version text not null,
  workflow_name text not null,
  workflow_version text not null,
  status text not null default 'created'
    check (status in ('created', 'running', 'completed', 'failed', 'expired', 'revoked')),
  max_iterations integer not null check (max_iterations between 1 and 10),
  expires_at timestamptz not null,
  started_at timestamptz,
  completed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint agent_sessions_expiry_check check (expires_at > created_at),
  constraint agent_sessions_completion_check check (
    status not in ('completed', 'failed', 'expired', 'revoked')
    or completed_at is not null
  )
);

comment on table public.agent_sessions is
  'CRAVE-030B: controlled agent identity/purpose/policy/owner/expiry state; never an unrestricted chat session.';

create table if not exists public.tool_call_log (
  id uuid primary key default gen_random_uuid(),
  agent_session_id uuid not null references public.agent_sessions(id) on update restrict on delete restrict,
  query_id uuid references public.ai_queries(id) on update restrict on delete restrict,
  retrieval_log_id uuid references public.retrieval_log(id) on update restrict on delete restrict,
  user_id uuid not null references public.user_profiles(id) on update restrict on delete restrict,
  workflow_name text not null,
  workflow_version text not null,
  tool_name text not null,
  tool_version text not null,
  input_hash text,
  output_hash text,
  input_summary jsonb not null default '{}'::jsonb,
  output_summary jsonb not null default '{}'::jsonb,
  status text not null check (status in ('started', 'succeeded', 'failed', 'denied')),
  duration_ms integer check (duration_ms is null or duration_ms >= 0),
  error_code text,
  created_at timestamptz not null default now(),
  constraint tool_call_input_hash_check check (input_hash is null or input_hash ~ '^[0-9a-f]{64}$'),
  constraint tool_call_output_hash_check check (output_hash is null or output_hash ~ '^[0-9a-f]{64}$'),
  constraint tool_call_status_check check (
    status <> 'failed' or nullif(trim(error_code), '') is not null
  )
);

comment on table public.tool_call_log is
  'CRAVE-030B: append-only allowlisted tool invocation evidence; summaries must exclude secrets/raw payload excess.';

create table if not exists public.system_health_metrics (
  id uuid primary key default gen_random_uuid(),
  metric_name text not null check (metric_name ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  numeric_value numeric,
  text_value text,
  status text not null default 'unknown' check (status in ('healthy', 'warning', 'critical', 'unknown')),
  labels jsonb not null default '{}'::jsonb,
  source_name text not null,
  measured_at timestamptz not null default now(),
  workflow_run_id uuid references public.workflow_runs(id) on update restrict on delete restrict,
  created_at timestamptz not null default now(),
  constraint system_health_metric_value_check check (
    (numeric_value is not null)::integer + (text_value is not null)::integer = 1
  )
);

comment on table public.system_health_metrics is
  'CRAVE-030B: append-only health observations with timestamp/source and no sensitive payload.';

alter table public.ai_query_sources
  add column if not exists document_version_id uuid,
  add column if not exists retrieval_candidate_id uuid,
  add column if not exists final_score double precision,
  add column if not exists citation_verified_at timestamptz;

comment on column public.ai_query_sources.document_version_id is
  'CRAVE-030B: immutable version cited by the selected chunk.';
comment on column public.ai_query_sources.retrieval_candidate_id is
  'CRAVE-030B: selected retrieval candidate that produced this citation when available.';
comment on column public.ai_query_sources.final_score is
  'CRAVE-030B: selected candidate final score captured at citation time.';
comment on column public.ai_query_sources.citation_verified_at is
  'CRAVE-030B: server-side time when exact claim/chunk/version lineage was verified.';

update public.ai_query_sources source
set document_version_id = chunk.document_version_id
from public.document_chunks chunk
where source.document_version_id is null
  and chunk.id = source.chunk_id;

do $citation_pre_constraint_assert$
declare
  missing_version bigint;
  invalid_version bigint;
begin
  select count(*) into missing_version
  from public.ai_query_sources
  where document_version_id is null;

  select count(*) into invalid_version
  from public.ai_query_sources source
  join public.document_chunks chunk on chunk.id = source.chunk_id
  where source.document_version_id is distinct from chunk.document_version_id
    or source.document_id is distinct from chunk.document_id
    or source.document_code is distinct from chunk.document_code
    or source.document_version is distinct from chunk.document_version;

  if missing_version <> 0 or invalid_version <> 0 then
    raise exception 'CRAVE-030B: citation lineage preflight fail missing_version=% invalid_version=%.',
      missing_version, invalid_version;
  end if;
end
$citation_pre_constraint_assert$;

do $foreign_keys$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_document_version_id_fkey'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_document_version_id_fkey
      foreign key (document_version_id)
      references public.document_versions(id)
      on update restrict on delete restrict;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_retrieval_candidate_id_fkey'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_retrieval_candidate_id_fkey
      foreign key (retrieval_candidate_id)
      references public.retrieval_candidates(id)
      on update restrict on delete restrict;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_grounded_verification_check'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_grounded_verification_check
      check (
        not grounded
        or (
          nullif(trim(claim_text), '') is not null
          and citation_rank is not null
          and citation_rank > 0
          and retrieval_candidate_id is not null
          and citation_verified_at is not null
        )
      );
  end if;
end
$foreign_keys$;

create or replace function public.crave_validate_ai_query_source_lineage()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $function$
declare
  linked_document_id uuid;
  linked_document_code text;
  linked_version_label text;
  linked_version_id uuid;
  candidate_chunk_id uuid;
  candidate_version_id uuid;
  candidate_query_id uuid;
begin
  select
    chunk.document_id,
    chunk.document_code,
    chunk.document_version,
    chunk.document_version_id
  into
    linked_document_id,
    linked_document_code,
    linked_version_label,
    linked_version_id
  from public.document_chunks chunk
  where chunk.id = new.chunk_id;

  if not found then
    raise exception 'CRAVE-030B: citation chunk_id không tồn tại.';
  end if;
  if new.document_version_id is distinct from linked_version_id
    or new.document_id is distinct from linked_document_id
    or new.document_code is distinct from linked_document_code
    or new.document_version is distinct from linked_version_label
  then
    raise exception 'CRAVE-030B: citation không khớp exact chunk/document/version lineage.';
  end if;

  if new.retrieval_candidate_id is not null then
    select candidate.chunk_id, candidate.document_version_id, log.query_id
    into candidate_chunk_id, candidate_version_id, candidate_query_id
    from public.retrieval_candidates candidate
    join public.retrieval_log log on log.id = candidate.retrieval_log_id
    where candidate.id = new.retrieval_candidate_id
      and candidate.selected = true;

    if not found
      or candidate_chunk_id is distinct from new.chunk_id
      or candidate_version_id is distinct from new.document_version_id
      or candidate_query_id is distinct from new.query_id
    then
      raise exception 'CRAVE-030B: citation không khớp selected retrieval candidate/query.';
    end if;
  end if;

  if new.grounded and new.citation_verified_at is null then
    new.citation_verified_at := clock_timestamp();
  end if;
  return new;
end
$function$;

comment on function public.crave_validate_ai_query_source_lineage() is
  'CRAVE-030B: exact citation-to-selected-candidate/chunk/current immutable-version lineage validator.';

do $citation_trigger$
begin
  if exists (
    select 1 from pg_trigger
    where tgrelid = 'public.ai_query_sources'::regclass
      and tgname = 'ai_query_sources_validate_lineage'
      and pg_get_triggerdef(oid) not like '%crave_validate_ai_query_source_lineage%'
  ) then
    raise exception 'CRAVE-030B: citation lineage trigger cùng tên không tương thích.';
  end if;
  if not exists (
    select 1 from pg_trigger
    where tgrelid = 'public.ai_query_sources'::regclass
      and tgname = 'ai_query_sources_validate_lineage'
  ) then
    create trigger ai_query_sources_validate_lineage
      before insert or update of
        query_id, chunk_id, document_id, document_code, document_version,
        document_version_id, retrieval_candidate_id, grounded, citation_verified_at
      on public.ai_query_sources
      for each row execute function public.crave_validate_ai_query_source_lineage();
  end if;
end
$citation_trigger$;

alter table public.ai_query_sources
  alter column document_version_id set not null;

create index if not exists idx_retrieval_profiles_status_version
  on public.retrieval_profiles (status, profile_name, profile_version);
create index if not exists idx_retrieval_log_user_created
  on public.retrieval_log (user_id, created_at desc);
create index if not exists idx_retrieval_log_query_created
  on public.retrieval_log (query_id, created_at desc);
create index if not exists idx_retrieval_candidates_rank
  on public.retrieval_candidates (retrieval_log_id, final_rank);
create index if not exists idx_retrieval_candidates_version
  on public.retrieval_candidates (document_version_id, selected);
create index if not exists idx_agent_sessions_user_status
  on public.agent_sessions (user_id, status, created_at desc);
create index if not exists idx_agent_sessions_expiry
  on public.agent_sessions (expires_at, status);
create index if not exists idx_tool_call_session_created
  on public.tool_call_log (agent_session_id, created_at);
create index if not exists idx_tool_call_query_created
  on public.tool_call_log (query_id, created_at) where query_id is not null;
create index if not exists idx_health_metric_time
  on public.system_health_metrics (metric_name, measured_at desc);
create index if not exists idx_ai_query_sources_document_version
  on public.ai_query_sources (document_version_id, created_at);
create index if not exists idx_ai_query_sources_retrieval_candidate
  on public.ai_query_sources (retrieval_candidate_id)
  where retrieval_candidate_id is not null;

alter table public.retrieval_profiles enable row level security;
alter table public.retrieval_log enable row level security;
alter table public.retrieval_candidates enable row level security;
alter table public.agent_sessions enable row level security;
alter table public.tool_call_log enable row level security;
alter table public.system_health_metrics enable row level security;

revoke all on table
  public.retrieval_profiles,
  public.retrieval_log,
  public.retrieval_candidates,
  public.agent_sessions,
  public.tool_call_log,
  public.system_health_metrics
from public, anon, authenticated;

grant select on table
  public.retrieval_profiles,
  public.retrieval_log,
  public.retrieval_candidates,
  public.agent_sessions,
  public.tool_call_log,
  public.system_health_metrics
to authenticated;

do $policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'retrieval_profiles'
      and policyname = 'retrieval_profiles_read_approved_or_auditor'
  ) then
    create policy retrieval_profiles_read_approved_or_auditor
      on public.retrieval_profiles for select to authenticated
      using (
        status = 'approved'
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'retrieval_log'
      and policyname = 'retrieval_log_read_own_or_auditor'
  ) then
    create policy retrieval_log_read_own_or_auditor
      on public.retrieval_log for select to authenticated
      using (
        user_id = auth.uid()
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'retrieval_candidates'
      and policyname = 'retrieval_candidates_read_own_or_auditor'
  ) then
    create policy retrieval_candidates_read_own_or_auditor
      on public.retrieval_candidates for select to authenticated
      using (
        exists (
          select 1 from public.retrieval_log log
          where log.id = retrieval_log_id and log.user_id = auth.uid()
        )
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'agent_sessions'
      and policyname = 'agent_sessions_read_own_or_auditor'
  ) then
    create policy agent_sessions_read_own_or_auditor
      on public.agent_sessions for select to authenticated
      using (
        user_id = auth.uid()
        or owner_id = auth.uid()
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'tool_call_log'
      and policyname = 'tool_call_log_read_own_or_auditor'
  ) then
    create policy tool_call_log_read_own_or_auditor
      on public.tool_call_log for select to authenticated
      using (
        user_id = auth.uid()
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'system_health_metrics'
      and policyname = 'system_health_metrics_read_auditor'
  ) then
    create policy system_health_metrics_read_auditor
      on public.system_health_metrics for select to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name,
        'auditor'::public.user_role_name
      ]));
  end if;
end
$policies$;

do $append_only_triggers$
declare
  target_table text;
  trigger_name text;
begin
  foreach target_table in array array[
    'retrieval_profiles',
    'retrieval_log',
    'retrieval_candidates',
    'tool_call_log',
    'system_health_metrics',
    'ai_query_sources'
  ] loop
    trigger_name := target_table || '_append_only_guard';
    if exists (
      select 1
      from pg_trigger trigger_row
      where trigger_row.tgrelid = to_regclass(format('public.%I', target_table))
        and trigger_row.tgname = trigger_name
        and trigger_row.tgfoid <> to_regprocedure('public.crave_block_append_only_mutation()')
    ) then
      raise exception 'CRAVE-030B: trigger % trên public.% không tương thích.', trigger_name, target_table;
    end if;
    if not exists (
      select 1
      from pg_trigger trigger_row
      where trigger_row.tgrelid = to_regclass(format('public.%I', target_table))
        and trigger_row.tgname = trigger_name
    ) then
      execute format(
        'create trigger %I before update or delete or truncate on public.%I '
        'for each statement execute function public.crave_block_append_only_mutation()',
        trigger_name,
        target_table
      );
    end if;
  end loop;
end
$append_only_triggers$;

do $final_assert$
declare
  target_table text;
  missing_rls bigint;
  citation_mismatch bigint;
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
      raise exception 'CRAVE-030B: thiếu bảng sau apply public.%.', target_table;
    end if;
  end loop;

  select count(*) into missing_rls
  from pg_class class_row
  join pg_namespace namespace_row on namespace_row.oid = class_row.relnamespace
  where namespace_row.nspname = 'public'
    and class_row.relname = any(array[
      'retrieval_profiles', 'retrieval_log', 'retrieval_candidates',
      'agent_sessions', 'tool_call_log', 'system_health_metrics'
    ])
    and not class_row.relrowsecurity;

  select count(*) into citation_mismatch
  from public.ai_query_sources source
  join public.document_chunks chunk on chunk.id = source.chunk_id
  where source.document_version_id is distinct from chunk.document_version_id;

  if missing_rls <> 0 or citation_mismatch <> 0 then
    raise exception 'CRAVE-030B: final assert fail missing_rls=% citation_mismatch=%.',
      missing_rls, citation_mismatch;
  end if;
end
$final_assert$;

commit;
