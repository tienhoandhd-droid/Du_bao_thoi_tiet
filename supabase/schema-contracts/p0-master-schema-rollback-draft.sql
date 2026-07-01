-- ============================================================================
-- CRAVE P0 MASTER SCHEMA ROLLBACK — ARCHITECTURAL DRAFT / NOT FOR APPLY
-- This is a dependency map, not an approved production rollback.
-- ============================================================================

begin;

-- Fail closed once evidence/data exists. Real migrations use compatibility
-- rollback and preserve append-only/version/review/eval records.
do $$
declare
  t text;
  n bigint;
begin
  foreach t in array array[
    'document_versions','retrieval_log','retrieval_candidates','tool_call_log',
    'generated_docs','doc_reviews','eval_failures'
  ] loop
    if to_regclass(format('public.%I', t)) is not null then
      execute format('select count(*) from public.%I', t) into n;
      if n > 0 then
        raise exception
          'Refusing destructive master rollback: %.% contains % rows; use compatibility/manual recovery',
          'public', t, n;
      end if;
    end if;
  end loop;
end $$;

-- Reverse optional FKs/columns only before consumer activation/backfill.
alter table if exists public.ai_query_sources
  drop constraint if exists ai_query_sources_retrieval_candidate_id_fkey,
  drop constraint if exists ai_query_sources_document_version_id_fkey,
  drop column if exists citation_verified_at,
  drop column if exists final_score,
  drop column if exists retrieval_candidate_id,
  drop column if exists document_version_id;

alter table if exists public.ai_queries
  drop constraint if exists ai_queries_retrieval_log_id_fkey,
  drop column if exists generation_skipped,
  drop column if exists no_source_reason,
  drop column if exists search_mode,
  drop column if exists retrieval_profile_version,
  drop column if exists retrieval_log_id,
  drop column if exists query_expanded,
  drop column if exists query_normalized;

alter table if exists public.document_chunks
  drop constraint if exists document_chunks_chunk_sha256_check,
  drop constraint if exists document_chunks_document_version_id_fkey,
  drop column if exists index_version,
  drop column if exists embedded_at,
  drop column if exists embedding_status,
  drop column if exists embedding_input_sha256,
  drop column if exists embedding_dimensions,
  drop column if exists embedding_model,
  drop column if exists tokenizer_version,
  drop column if exists tokenizer_name,
  drop column if exists is_ocr,
  drop column if exists is_table,
  drop column if exists heading_path,
  drop column if exists page_end,
  drop column if exists page_start,
  drop column if exists chunk_sha256,
  drop column if exists document_version_id;

alter table if exists public.documents
  drop constraint if exists documents_current_version_id_fkey,
  drop column if exists current_version_id;

alter table if exists public.eval_runs
  drop constraint if exists eval_runs_prompt_version_id_fkey,
  drop constraint if exists eval_runs_retrieval_profile_id_fkey,
  drop constraint if exists eval_runs_dataset_id_fkey,
  drop column if exists summary,
  drop column if exists corpus_snapshot_sha256,
  drop column if exists workflow_versions,
  drop column if exists git_commit,
  drop column if exists prompt_version_id,
  drop column if exists retrieval_profile_id,
  drop column if exists dataset_id;

alter table if exists public.golden_questions
  drop constraint if exists golden_questions_dataset_id_fkey,
  drop column if exists dataset_id;

alter table if exists public.prompt_versions
  drop constraint if exists prompt_versions_prompt_sha256_check,
  drop column if exists metadata,
  drop column if exists git_commit,
  drop column if exists prompt_sha256;

drop table if exists public.system_health_metrics;
drop table if exists public.eval_failures;
drop table if exists public.eval_datasets;
drop table if exists public.approved_doc_snapshots;
drop table if exists public.doc_review_findings;
drop table if exists public.doc_reviews;
drop table if exists public.generated_doc_sections;
drop table if exists public.generated_docs;
drop table if exists public.tool_call_log;
drop table if exists public.retrieval_candidates;
drop table if exists public.retrieval_log;
drop table if exists public.query_rewrite_log;
drop table if exists public.retrieval_profiles;
drop table if exists public.glossary_terms;
drop table if exists public.document_tags;
drop table if exists public.document_classifications;
drop table if exists public.document_parse_jobs;
drop table if exists public.document_versions;
drop table if exists public.raw_files;
drop table if exists public.source_discovered_items;
drop table if exists public.source_crawl_runs;
drop table if exists public.license_rules;
drop table if exists public.source_registry;

-- Architectural draft must never persist when tested as one file.
rollback;
