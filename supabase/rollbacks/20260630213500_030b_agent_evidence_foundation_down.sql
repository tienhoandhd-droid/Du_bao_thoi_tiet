-- CRAVE rollback: 20260630213500_030b_agent_evidence_foundation
-- Chỉ rollback trước khi có evidence. Khi bảng có dữ liệu, dùng compatibility/
-- manual recovery; không được xóa audit/retrieval/tool/citation evidence.

begin;

do $rollback_guard$
declare
  target_table text;
  row_count bigint;
begin
  foreach target_table in array array[
    'retrieval_profiles',
    'retrieval_log',
    'retrieval_candidates',
    'agent_sessions',
    'tool_call_log',
    'system_health_metrics'
  ] loop
    if to_regclass(format('public.%I', target_table)) is not null then
      execute format('select count(*) from public.%I', target_table) into row_count;
      if row_count <> 0 then
        raise exception
          'CRAVE-030B rollback từ chối: public.% có % evidence rows; dùng manual compatibility recovery.',
          target_table,
          row_count;
      end if;
    end if;
  end loop;

  if to_regclass('public.ai_query_sources') is not null and exists (
    select 1
    from public.ai_query_sources
    where retrieval_candidate_id is not null
      or citation_verified_at is not null
  ) then
    raise exception 'CRAVE-030B rollback từ chối: ai_query_sources đã dùng citation evidence mới.';
  end if;
end
$rollback_guard$;

drop trigger if exists ai_query_sources_append_only_guard on public.ai_query_sources;
drop trigger if exists ai_query_sources_validate_lineage on public.ai_query_sources;
drop function if exists public.crave_validate_ai_query_source_lineage();

drop trigger if exists retrieval_candidates_validate_lineage on public.retrieval_candidates;
drop trigger if exists retrieval_log_validate_context on public.retrieval_log;
drop function if exists public.crave_validate_retrieval_candidate_lineage();
drop function if exists public.crave_validate_retrieval_log_context();

alter table if exists public.ai_query_sources
  drop constraint if exists ai_query_sources_grounded_verification_check,
  drop constraint if exists ai_query_sources_retrieval_candidate_id_fkey,
  drop constraint if exists ai_query_sources_document_version_id_fkey,
  drop column if exists citation_verified_at,
  drop column if exists final_score,
  drop column if exists retrieval_candidate_id,
  drop column if exists document_version_id;

alter table if exists public.ai_queries
  drop constraint if exists ai_queries_no_source_check,
  drop constraint if exists ai_queries_search_mode_check,
  drop column if exists generation_skipped,
  drop column if exists no_source_reason,
  drop column if exists search_mode,
  drop column if exists retrieval_profile_version,
  drop column if exists query_expanded,
  drop column if exists query_normalized;

drop table if exists public.system_health_metrics;
drop table if exists public.tool_call_log;
drop table if exists public.agent_sessions;
drop table if exists public.retrieval_candidates;
drop table if exists public.retrieval_log;
drop table if exists public.retrieval_profiles;

commit;
