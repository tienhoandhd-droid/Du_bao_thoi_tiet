-- ============================================================================
-- CRAVE P0 MASTER SCHEMA — ARCHITECTURAL DRAFT / NOT FOR APPLY
-- Project: bdttccztjtrcaztjgkot
-- Purpose: coverage review only. Split into migrations 024–032 before execution.
-- ============================================================================

begin;

create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto with schema extensions;

-- SOURCE / CRAWL -------------------------------------------------------------

create table if not exists public.source_registry (
  id uuid primary key default gen_random_uuid(),
  source_name text not null,
  domain text not null,
  organization text not null,
  access_mode text not null check (access_mode in ('allow','curated','metadata_only','deny')),
  trust_level integer not null default 3 check (trust_level between 1 and 5),
  public_only boolean not null default true,
  robots_required boolean not null default true,
  crawl_delay_seconds integer not null default 30 check (crawl_delay_seconds >= 0),
  allowed_content_types text[] not null default '{}',
  seed_urls text[] not null default '{}',
  license_summary text,
  owner_id uuid,
  approved_by uuid,
  approved_at timestamptz,
  effective_from timestamptz,
  effective_until timestamptz,
  is_active boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint source_registry_domain_key unique (domain),
  constraint source_registry_approval_check check (
    not is_active or (approved_by is not null and approved_at is not null)
  )
);

create table if not exists public.license_rules (
  id uuid primary key default gen_random_uuid(),
  source_registry_id uuid not null references public.source_registry(id),
  content_pattern text not null,
  decision text not null check (decision in ('allow','curated','metadata_only','deny')),
  reason text not null,
  evidence_url text,
  effective_from timestamptz not null default now(),
  effective_until timestamptz,
  approved_by uuid not null,
  approved_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint license_rules_window_check check (
    effective_until is null or effective_until > effective_from
  )
);

create table if not exists public.source_crawl_runs (
  id uuid primary key default gen_random_uuid(),
  source_registry_id uuid not null references public.source_registry(id),
  workflow_run_id uuid references public.workflow_runs(id),
  status text not null default 'running'
    check (status in ('running','succeeded','partial','failed','cancelled')),
  discovered_count integer not null default 0 check (discovered_count >= 0),
  new_count integer not null default 0 check (new_count >= 0),
  changed_count integer not null default 0 check (changed_count >= 0),
  rejected_count integer not null default 0 check (rejected_count >= 0),
  error_code text,
  error_summary text,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.source_discovered_items (
  id uuid primary key default gen_random_uuid(),
  crawl_run_id uuid not null references public.source_crawl_runs(id),
  source_registry_id uuid not null references public.source_registry(id),
  canonical_url text not null,
  source_document_id text,
  title text,
  mime_type text,
  http_etag text,
  http_last_modified text,
  content_length bigint check (content_length is null or content_length >= 0),
  license_decision text not null
    check (license_decision in ('allow','curated','metadata_only','deny')),
  status text not null default 'discovered'
    check (status in ('discovered','queued','downloaded','metadata_only','rejected','failed')),
  idempotency_key text not null,
  discovered_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint source_discovered_items_idempotency_key unique (idempotency_key)
);

create table if not exists public.raw_files (
  id uuid primary key default gen_random_uuid(),
  source_item_id uuid references public.source_discovered_items(id),
  drive_file_id text not null,
  drive_folder_id text,
  file_name text not null,
  mime_type text not null,
  file_size_bytes bigint check (file_size_bytes is null or file_size_bytes >= 0),
  binary_sha256 text,
  hash_status text not null default 'pending'
    check (hash_status in ('pending','verified','legacy_missing','mismatch')),
  status text not null default 'stored'
    check (status in ('stored','verified','rejected','quarantined','failed')),
  stored_by uuid,
  stored_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint raw_files_drive_file_key unique (drive_file_id),
  constraint raw_files_sha256_check check (
    binary_sha256 is null or binary_sha256 ~ '^[0-9a-f]{64}$'
  )
);

-- DOCUMENT LIFECYCLE ---------------------------------------------------------

create table if not exists public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id),
  raw_file_id uuid references public.raw_files(id),
  source_registry_id uuid references public.source_registry(id),
  version_label text not null,
  source_document_id text,
  source_url text,
  source_updated_at timestamptz,
  effective_date date,
  retired_at timestamptz,
  superseded_by_version_id uuid references public.document_versions(id),
  drive_file_id text,
  binary_sha256 text,
  content_sha256 text,
  hash_status text not null default 'pending'
    check (hash_status in ('pending','verified','legacy_content_only','legacy_missing','mismatch')),
  license_status text not null default 'unknown'
    check (license_status in ('allowed','curated','metadata_only','denied','unknown')),
  parse_status text not null default 'pending'
    check (parse_status in ('pending','running','success','partial','failed','needs_review')),
  parse_quality_score numeric(5,2)
    check (parse_quality_score is null or parse_quality_score between 0 and 100),
  parse_engine text,
  parse_engine_version text,
  parsed_at timestamptz,
  parse_reviewed_by uuid,
  parse_reviewed_at timestamptz,
  approved_for_ai_use boolean not null default false,
  approved_by uuid,
  approved_at timestamptz,
  index_status text not null default 'not_ready'
    check (index_status in ('not_ready','queued','indexing','ready','failed','excluded')),
  index_version text,
  created_at timestamptz not null default now(),
  constraint document_versions_doc_label_key unique (document_id, version_label),
  constraint document_versions_binary_sha_check check (
    binary_sha256 is null or binary_sha256 ~ '^[0-9a-f]{64}$'
  ),
  constraint document_versions_content_sha_check check (
    content_sha256 is null or content_sha256 ~ '^[0-9a-f]{64}$'
  ),
  constraint document_versions_not_self_superseded check (
    superseded_by_version_id is null or superseded_by_version_id <> id
  ),
  constraint document_versions_ai_approval_check check (
    not approved_for_ai_use or (approved_by is not null and approved_at is not null)
  )
);

alter table public.documents
  add column if not exists current_version_id uuid;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'documents_current_version_id_fkey'
      and conrelid = 'public.documents'::regclass
  ) then
    alter table public.documents
      add constraint documents_current_version_id_fkey
      foreign key (current_version_id) references public.document_versions(id);
  end if;
end $$;

alter table public.document_chunks
  add column if not exists document_version_id uuid,
  add column if not exists chunk_sha256 text,
  add column if not exists page_start integer,
  add column if not exists page_end integer,
  add column if not exists heading_path text[],
  add column if not exists is_table boolean not null default false,
  add column if not exists is_ocr boolean not null default false,
  add column if not exists tokenizer_name text,
  add column if not exists tokenizer_version text,
  add column if not exists embedding_model text,
  add column if not exists embedding_dimensions integer,
  add column if not exists embedding_input_sha256 text,
  add column if not exists embedding_status text not null default 'missing',
  add column if not exists embedded_at timestamptz,
  add column if not exists index_version text;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'document_chunks_document_version_id_fkey'
      and conrelid = 'public.document_chunks'::regclass
  ) then
    alter table public.document_chunks
      add constraint document_chunks_document_version_id_fkey
      foreign key (document_version_id) references public.document_versions(id);
  end if;
  if not exists (
    select 1 from pg_constraint
    where conname = 'document_chunks_chunk_sha256_check'
      and conrelid = 'public.document_chunks'::regclass
  ) then
    alter table public.document_chunks add constraint document_chunks_chunk_sha256_check
      check (chunk_sha256 is null or chunk_sha256 ~ '^[0-9a-f]{64}$') not valid;
  end if;
end $$;

create table if not exists public.document_parse_jobs (
  id uuid primary key default gen_random_uuid(),
  raw_file_id uuid not null references public.raw_files(id),
  document_version_id uuid references public.document_versions(id),
  job_type text not null default 'parse'
    check (job_type in ('parse','reparse','chunk','embed','reindex')),
  status text not null default 'queued'
    check (status in ('queued','leased','succeeded','partial','failed','dead_letter','cancelled')),
  idempotency_key text not null unique,
  parser_name text,
  parser_version text,
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  leased_until timestamptz,
  worker_id text,
  error_code text,
  error_summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint document_parse_jobs_attempts_check check (attempts <= max_attempts)
);

create table if not exists public.document_classifications (
  id uuid primary key default gen_random_uuid(),
  document_version_id uuid not null references public.document_versions(id),
  class_key text not null,
  class_value text not null,
  method text not null check (method in ('rule','model','human')),
  confidence numeric(5,4) check (confidence is null or confidence between 0 and 1),
  status text not null default 'proposed'
    check (status in ('proposed','approved','rejected','retired')),
  model_used text,
  prompt_version_id uuid references public.prompt_versions(id),
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.document_tags (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id),
  document_version_id uuid references public.document_versions(id),
  tag_type text not null,
  tag_value text not null,
  source text not null default 'human' check (source in ('rule','model','human')),
  created_by uuid,
  created_at timestamptz not null default now(),
  constraint document_tags_unique unique (document_id, document_version_id, tag_type, tag_value)
);

-- RETRIEVAL / RAG ------------------------------------------------------------

create table if not exists public.glossary_terms (
  id uuid primary key default gen_random_uuid(),
  term_en text not null,
  term_vi text not null,
  abbreviation text,
  synonyms jsonb not null default '[]'::jsonb,
  domain text not null default 'gmp',
  do_not_translate boolean not null default false,
  status text not null default 'draft'
    check (status in ('draft','approved','retired')),
  version text not null default '1',
  source_reference text,
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint glossary_terms_unique unique (term_en, domain, version),
  constraint glossary_terms_approval_check check (
    status <> 'approved' or (approved_by is not null and approved_at is not null)
  )
);

create table if not exists public.retrieval_profiles (
  id uuid primary key default gen_random_uuid(),
  profile_name text not null,
  profile_version text not null,
  embedding_model text not null,
  embedding_dimensions integer not null check (embedding_dimensions > 0),
  fts_pool_size integer not null check (fts_pool_size between 1 and 200),
  vector_pool_size integer not null check (vector_pool_size between 1 and 200),
  final_top_k integer not null check (final_top_k between 1 and 50),
  rrf_k integer not null default 60 check (rrf_k > 0),
  score_threshold numeric,
  weights jsonb not null default '{}'::jsonb,
  status text not null default 'draft' check (status in ('draft','approved','retired')),
  git_commit text,
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  constraint retrieval_profiles_name_version_key unique (profile_name, profile_version)
);

alter table public.ai_queries
  add column if not exists query_normalized text,
  add column if not exists query_expanded text,
  add column if not exists retrieval_log_id uuid,
  add column if not exists retrieval_profile_version text,
  add column if not exists search_mode text,
  add column if not exists no_source_reason text,
  add column if not exists generation_skipped boolean not null default false;

create table if not exists public.query_rewrite_log (
  id uuid primary key default gen_random_uuid(),
  query_id uuid not null references public.ai_queries(id),
  original_query text not null,
  normalized_query text not null,
  expanded_query text not null,
  expansion_source text not null check (expansion_source in ('glossary','model','mixed','fallback')),
  glossary_version text,
  prompt_version_id uuid references public.prompt_versions(id),
  model_used text,
  status text not null check (status in ('succeeded','fallback','failed')),
  created_at timestamptz not null default now()
);

create table if not exists public.retrieval_log (
  id uuid primary key default gen_random_uuid(),
  query_id uuid not null references public.ai_queries(id),
  user_id uuid not null,
  profile_id uuid not null references public.retrieval_profiles(id),
  workflow_name text not null,
  workflow_version text not null,
  search_mode text not null check (search_mode in ('hybrid','fts_only','vector_only','no_source')),
  filters jsonb not null default '{}'::jsonb,
  fts_candidate_count integer not null default 0,
  vector_candidate_count integer not null default 0,
  selected_count integer not null default 0,
  no_source_reason text,
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  created_at timestamptz not null default now()
);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'ai_queries_retrieval_log_id_fkey'
      and conrelid = 'public.ai_queries'::regclass
  ) then
    alter table public.ai_queries add constraint ai_queries_retrieval_log_id_fkey
      foreign key (retrieval_log_id) references public.retrieval_log(id);
  end if;
end $$;

create table if not exists public.retrieval_candidates (
  id uuid primary key default gen_random_uuid(),
  retrieval_log_id uuid not null references public.retrieval_log(id),
  chunk_id uuid not null references public.document_chunks(id),
  document_version_id uuid not null references public.document_versions(id),
  fts_rank integer,
  vector_rank integer,
  fts_score double precision,
  vector_score double precision,
  rrf_score double precision not null,
  metadata_boost double precision not null default 0,
  final_score double precision not null,
  final_rank integer check (final_rank is null or final_rank > 0),
  selected boolean not null default false,
  rejection_reason text,
  created_at timestamptz not null default now(),
  constraint retrieval_candidates_unique unique (retrieval_log_id, chunk_id)
);

alter table public.ai_query_sources
  add column if not exists document_version_id uuid,
  add column if not exists retrieval_candidate_id uuid,
  add column if not exists final_score double precision,
  add column if not exists citation_verified_at timestamptz;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'ai_query_sources_document_version_id_fkey'
      and conrelid = 'public.ai_query_sources'::regclass
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_document_version_id_fkey
      foreign key (document_version_id) references public.document_versions(id);
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'ai_query_sources_retrieval_candidate_id_fkey'
      and conrelid = 'public.ai_query_sources'::regclass
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_retrieval_candidate_id_fkey
      foreign key (retrieval_candidate_id) references public.retrieval_candidates(id);
  end if;
end $$;

-- AGENT / TOOL ----------------------------------------------------------------

create table if not exists public.tool_call_log (
  id uuid primary key default gen_random_uuid(),
  query_id uuid references public.ai_queries(id),
  session_id text,
  workflow_name text not null,
  workflow_version text not null,
  tool_name text not null,
  tool_version text,
  input_hash text,
  output_hash text,
  input_summary jsonb not null default '{}'::jsonb,
  output_summary jsonb not null default '{}'::jsonb,
  status text not null check (status in ('started','succeeded','failed','denied')),
  duration_ms integer check (duration_ms is null or duration_ms >= 0),
  error_code text,
  created_at timestamptz not null default now(),
  constraint tool_call_input_hash_check check (input_hash is null or input_hash ~ '^[0-9a-f]{64}$'),
  constraint tool_call_output_hash_check check (output_hash is null or output_hash ~ '^[0-9a-f]{64}$')
);

-- GENERATED DOCUMENTS --------------------------------------------------------

create table if not exists public.generated_docs (
  id uuid primary key default gen_random_uuid(),
  created_by uuid not null,
  document_type text not null,
  title text not null,
  google_doc_id text,
  status text not null default 'draft'
    check (status in ('draft','review','changes_requested','approved','rejected','archived')),
  source_query_id uuid references public.ai_queries(id),
  retrieval_log_id uuid references public.retrieval_log(id),
  template_id uuid references public.validation_templates(id),
  template_version text,
  prompt_version_id uuid references public.prompt_versions(id),
  model_used text,
  generated_by_ai boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint generated_docs_ai_source_check check (
    not generated_by_ai or (source_query_id is not null and retrieval_log_id is not null)
  )
);

create table if not exists public.generated_doc_sections (
  id uuid primary key default gen_random_uuid(),
  generated_doc_id uuid not null references public.generated_docs(id),
  section_key text not null,
  section_order integer not null check (section_order >= 0),
  title text,
  content text not null,
  source_chunk_ids uuid[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint generated_doc_sections_key unique (generated_doc_id, section_key)
);

create table if not exists public.doc_reviews (
  id uuid primary key default gen_random_uuid(),
  generated_doc_id uuid not null references public.generated_docs(id),
  reviewer_id uuid not null,
  review_status text not null
    check (review_status in ('review_started','changes_requested','approved','rejected')),
  comments text,
  created_at timestamptz not null default now()
);

create table if not exists public.doc_review_findings (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null references public.doc_reviews(id),
  severity text not null check (severity in ('critical','major','minor','observation')),
  location text,
  finding text not null,
  recommendation text,
  evidence_document_version_id uuid references public.document_versions(id),
  evidence_chunk_id uuid references public.document_chunks(id),
  created_at timestamptz not null default now()
);

create table if not exists public.approved_doc_snapshots (
  id uuid primary key default gen_random_uuid(),
  generated_doc_id uuid not null references public.generated_docs(id),
  review_id uuid not null references public.doc_reviews(id),
  drive_file_id text not null,
  pdf_sha256 text not null check (pdf_sha256 ~ '^[0-9a-f]{64}$'),
  approved_by uuid not null,
  approved_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint approved_doc_snapshots_hash_key unique (pdf_sha256)
);

-- EVAL / HEALTH --------------------------------------------------------------

create table if not exists public.eval_datasets (
  id uuid primary key default gen_random_uuid(),
  dataset_name text not null,
  dataset_version text not null,
  file_path text not null,
  file_sha256 text not null check (file_sha256 ~ '^[0-9a-f]{64}$'),
  status text not null default 'draft' check (status in ('draft','approved','retired')),
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  constraint eval_datasets_name_version_key unique (dataset_name, dataset_version)
);

alter table public.golden_questions add column if not exists dataset_id uuid;
alter table public.prompt_versions
  add column if not exists prompt_sha256 text,
  add column if not exists git_commit text,
  add column if not exists metadata jsonb not null default '{}'::jsonb;
alter table public.eval_runs
  add column if not exists dataset_id uuid,
  add column if not exists retrieval_profile_id uuid,
  add column if not exists prompt_version_id uuid,
  add column if not exists git_commit text,
  add column if not exists workflow_versions jsonb,
  add column if not exists corpus_snapshot_sha256 text,
  add column if not exists summary jsonb not null default '{}'::jsonb;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'golden_questions_dataset_id_fkey'
      and conrelid = 'public.golden_questions'::regclass
  ) then
    alter table public.golden_questions add constraint golden_questions_dataset_id_fkey
      foreign key (dataset_id) references public.eval_datasets(id);
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'eval_runs_dataset_id_fkey'
      and conrelid = 'public.eval_runs'::regclass
  ) then
    alter table public.eval_runs add constraint eval_runs_dataset_id_fkey
      foreign key (dataset_id) references public.eval_datasets(id);
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'eval_runs_retrieval_profile_id_fkey'
      and conrelid = 'public.eval_runs'::regclass
  ) then
    alter table public.eval_runs add constraint eval_runs_retrieval_profile_id_fkey
      foreign key (retrieval_profile_id) references public.retrieval_profiles(id);
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'eval_runs_prompt_version_id_fkey'
      and conrelid = 'public.eval_runs'::regclass
  ) then
    alter table public.eval_runs add constraint eval_runs_prompt_version_id_fkey
      foreign key (prompt_version_id) references public.prompt_versions(id);
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'prompt_versions_prompt_sha256_check'
      and conrelid = 'public.prompt_versions'::regclass
  ) then
    alter table public.prompt_versions add constraint prompt_versions_prompt_sha256_check
      check (prompt_sha256 is null or prompt_sha256 ~ '^[0-9a-f]{64}$') not valid;
  end if;
end $$;

create table if not exists public.eval_failures (
  id uuid primary key default gen_random_uuid(),
  eval_result_id uuid not null references public.eval_results(id),
  failure_type text not null,
  severity text not null check (severity in ('critical','major','minor')),
  status text not null default 'open' check (status in ('open','accepted','fixed','closed')),
  owner_id uuid,
  capa_reference text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.system_health_metrics (
  id uuid primary key default gen_random_uuid(),
  metric_name text not null,
  numeric_value numeric,
  text_value text,
  labels jsonb not null default '{}'::jsonb,
  measured_at timestamptz not null default now(),
  workflow_run_id uuid references public.workflow_runs(id),
  created_at timestamptz not null default now(),
  constraint system_health_metric_value_check check (
    numeric_value is not null or text_value is not null
  )
);

-- INDEXES --------------------------------------------------------------------

create index if not exists idx_license_rules_source_effective
  on public.license_rules (source_registry_id, effective_from desc);
create index if not exists idx_source_crawl_runs_source_started
  on public.source_crawl_runs (source_registry_id, started_at desc);
create index if not exists idx_source_items_source_status
  on public.source_discovered_items (source_registry_id, status);
create index if not exists idx_raw_files_hash on public.raw_files (binary_sha256)
  where binary_sha256 is not null;
create index if not exists idx_document_versions_doc_created
  on public.document_versions (document_id, created_at desc);
create index if not exists idx_document_versions_content_hash
  on public.document_versions (content_sha256) where content_sha256 is not null;
create index if not exists idx_document_chunks_version
  on public.document_chunks (document_version_id, chunk_index);
create index if not exists idx_parse_jobs_status_lease
  on public.document_parse_jobs (status, leased_until);
create index if not exists idx_document_classifications_version
  on public.document_classifications (document_version_id, status);
create index if not exists idx_document_tags_value
  on public.document_tags (tag_type, tag_value);
create index if not exists idx_glossary_terms_en on public.glossary_terms (lower(term_en));
create index if not exists idx_glossary_terms_vi on public.glossary_terms (lower(term_vi));
create index if not exists idx_rewrite_query_created on public.query_rewrite_log (query_id, created_at);
create index if not exists idx_retrieval_query_created on public.retrieval_log (query_id, created_at);
create index if not exists idx_retrieval_candidates_rank on public.retrieval_candidates (retrieval_log_id, final_rank);
create index if not exists idx_tool_call_session_created on public.tool_call_log (session_id, created_at);
create index if not exists idx_generated_docs_creator_status on public.generated_docs (created_by, status);
create index if not exists idx_doc_reviews_doc_created on public.doc_reviews (generated_doc_id, created_at);
create index if not exists idx_eval_failures_status on public.eval_failures (status, severity);
create index if not exists idx_health_metric_time on public.system_health_metrics (metric_name, measured_at desc);

-- RLS DEFAULT-DENY -----------------------------------------------------------

alter table public.source_registry enable row level security;
alter table public.license_rules enable row level security;
alter table public.source_crawl_runs enable row level security;
alter table public.source_discovered_items enable row level security;
alter table public.raw_files enable row level security;
alter table public.document_versions enable row level security;
alter table public.document_parse_jobs enable row level security;
alter table public.document_classifications enable row level security;
alter table public.document_tags enable row level security;
alter table public.glossary_terms enable row level security;
alter table public.retrieval_profiles enable row level security;
alter table public.query_rewrite_log enable row level security;
alter table public.retrieval_log enable row level security;
alter table public.retrieval_candidates enable row level security;
alter table public.tool_call_log enable row level security;
alter table public.generated_docs enable row level security;
alter table public.generated_doc_sections enable row level security;
alter table public.doc_reviews enable row level security;
alter table public.doc_review_findings enable row level security;
alter table public.approved_doc_snapshots enable row level security;
alter table public.eval_datasets enable row level security;
alter table public.eval_failures enable row level security;
alter table public.system_health_metrics enable row level security;

revoke all on table
  public.source_registry, public.license_rules, public.source_crawl_runs,
  public.source_discovered_items, public.raw_files, public.document_versions,
  public.document_parse_jobs, public.document_classifications, public.document_tags,
  public.glossary_terms, public.retrieval_profiles, public.query_rewrite_log,
  public.retrieval_log, public.retrieval_candidates, public.tool_call_log,
  public.generated_docs, public.generated_doc_sections, public.doc_reviews,
  public.doc_review_findings, public.approved_doc_snapshots, public.eval_datasets,
  public.eval_failures, public.system_health_metrics
from public, anon, authenticated;

-- SAMPLE POLICIES ONLY. Split/review per migration; backend writes should use
-- narrow RPCs instead of broad table grants.
do $$
begin
  if not exists (
    select 1 from pg_policies where schemaname='public'
      and tablename='source_registry' and policyname='source_registry_read_active'
  ) then
    create policy source_registry_read_active on public.source_registry
      for select to authenticated using (is_active = true);
  end if;
  if not exists (
    select 1 from pg_policies where schemaname='public'
      and tablename='glossary_terms' and policyname='glossary_terms_read_approved'
  ) then
    create policy glossary_terms_read_approved on public.glossary_terms
      for select to authenticated using (status = 'approved');
  end if;
  if not exists (
    select 1 from pg_policies where schemaname='public'
      and tablename='retrieval_log' and policyname='retrieval_log_read_own'
  ) then
    create policy retrieval_log_read_own on public.retrieval_log
      for select to authenticated using (user_id = auth.uid());
  end if;
  if not exists (
    select 1 from pg_policies where schemaname='public'
      and tablename='generated_docs' and policyname='generated_docs_read_own'
  ) then
    create policy generated_docs_read_own on public.generated_docs
      for select to authenticated using (created_by = auth.uid());
  end if;
end $$;

grant select on public.source_registry, public.glossary_terms to authenticated;
grant select on public.retrieval_log, public.generated_docs to authenticated;

-- UPDATED_AT SAMPLE TRIGGERS -------------------------------------------------
-- Reuses existing public.update_updated_at() if present.
do $$
declare
  t text;
begin
  if to_regprocedure('public.update_updated_at()') is null then
    raise exception 'Missing public.update_updated_at(); split migration must provide reviewed helper';
  end if;
  foreach t in array array[
    'source_registry','source_discovered_items','raw_files','document_parse_jobs',
    'glossary_terms','generated_docs','generated_doc_sections','eval_failures'
  ] loop
    if not exists (
      select 1 from pg_trigger
      where tgrelid = format('public.%I', t)::regclass
        and tgname = 'tr_' || t || '_updated'
    ) then
      execute format(
        'create trigger %I before update on public.%I for each row execute function public.update_updated_at()',
        'tr_' || t || '_updated', t
      );
    end if;
  end loop;
end $$;

comment on table public.document_versions is
  'Immutable document version provenance. Do not overwrite approved content.';
comment on table public.retrieval_log is
  'Append-only retrieval run evidence; detailed ranking in retrieval_candidates.';
comment on table public.tool_call_log is
  'Append-only controlled tool invocation evidence; not agent memory.';
comment on table public.generated_docs is
  'AI-created records remain DRAFT until an authorized human review transition.';

-- DO NOT COMMIT/APPLY THIS TRANSACTION AS A REAL MIGRATION.
-- Draft ends with rollback so accidental interactive execution does not persist.
rollback;
