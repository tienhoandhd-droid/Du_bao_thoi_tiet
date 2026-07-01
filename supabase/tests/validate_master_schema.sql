-- CRAVE master schema validation pack — READ ONLY
-- DRAFT: run individual sections only after the referenced migration exists.
-- Expected zero-row checks return no rows when PASS unless noted otherwise.

-- V00. Preflight object coverage.
-- Purpose: list required target tables that do not exist.
-- Expected: zero rows for the activated phase; DESIGN_ONLY P1/P2 may be excluded.
-- Fail action: do not run dependent queries/apply consumer workflow.
with required(table_name) as (
  values
    ('source_registry'), ('license_rules'), ('source_crawl_runs'),
    ('source_discovered_items'), ('raw_files'), ('documents'),
    ('document_versions'), ('document_chunks'), ('document_access'),
    ('document_parse_jobs'), ('document_classifications'), ('document_tags'),
    ('glossary_terms'), ('prompt_versions'), ('query_rewrite_log'),
    ('retrieval_log'), ('retrieval_candidates'), ('ai_queries'),
    ('ai_query_sources'), ('tool_call_log'), ('audit_log'),
    ('generated_docs'), ('doc_reviews'), ('eval_datasets'),
    ('golden_questions'), ('eval_runs'), ('eval_results'), ('eval_failures'),
    ('workflow_runs')
)
select r.table_name as missing_table
from required r
where to_regclass(format('public.%I', r.table_name)) is null
order by r.table_name;

-- V01. Empty tables.
-- Purpose: identify activated tables with no data; empty is not always failure.
-- Expected: every empty table has documented phase/fixture/owner.
-- Fail action: mark NO TEST DATA or UNUSED; seed synthetic data or defer creation.
select relname as table_name, n_live_tup as estimated_rows
from pg_stat_user_tables
where schemaname = 'public'
  and n_live_tup = 0
order by relname;

-- V02. Document versions without chunks.
-- Purpose: find AI-approved/index-ready versions with no retrieval units.
-- Expected: zero rows.
-- Fail action: set index_status failed/not_ready; enqueue controlled reindex.
select dv.id, dv.document_id, dv.version_label, dv.index_status
from public.document_versions dv
left join public.document_chunks dc on dc.document_version_id = dv.id
where dv.approved_for_ai_use = true
  and dv.index_status in ('ready', 'indexed')
group by dv.id, dv.document_id, dv.version_label, dv.index_status
having count(dc.id) = 0;

-- V03. Chunks without valid embedding metadata.
-- Purpose: prove vector corpus readiness.
-- Expected: zero required/indexed chunks.
-- Fail action: enqueue idempotent embedding jobs; do not claim hybrid-ready.
select id, document_version_id, chunk_index, embedding_status,
       embedding_model, embedding_dimensions
from public.document_chunks
where status::text = 'indexed'
  and (
    embedding is null
    or embedding_status <> 'ready'
    or embedding_model is null
    or embedding_dimensions <> 1536
    or embedding_input_sha256 is null
  );

-- V04. Generated docs without source query/retrieval lineage.
-- Purpose: prevent uncited AI draft.
-- Expected: zero AI-generated rows.
-- Fail action: block review/approval, attach retrieval evidence or invalidate draft.
select id, title, status, source_query_id, retrieval_log_id
from public.generated_docs
where generated_by_ai = true
  and (source_query_id is null or retrieval_log_id is null);

-- V05. AI queries without sources.
-- Purpose: detect answers with no citation mapping.
-- Expected: only explicit no_source/refused queries may have zero sources.
-- Fail action: invalidate answer, fix citation writer/transaction.
select q.id, q.user_id, q.created_at, q.search_mode
from public.ai_queries q
left join public.ai_query_sources s on s.query_id = q.id
where coalesce(q.search_mode, '') not in ('no_source', 'refused')
group by q.id, q.user_id, q.created_at, q.search_mode
having count(s.id) = 0;

-- V06. Successful parse without quality evidence.
-- Purpose: prevent default/unknown parse from entering AI corpus.
-- Expected: zero rows.
-- Fail action: set needs_review/not_ready and re-run/review parser output.
select id, document_id, version_label, parse_status, parse_quality_score,
       parse_engine, parse_engine_version
from public.document_versions
where parse_status = 'success'
  and (
    parse_quality_score is null
    or parse_engine is null
    or parse_engine_version is null
  );

-- V07. Raw files without document version or active parse job.
-- Purpose: detect broken raw→version pipeline.
-- Expected: zero stored/verified raw files older than SLA without downstream state.
-- Fail action: enqueue parse job or mark explicit rejected/duplicate status.
select rf.id, rf.drive_file_id, rf.status, rf.created_at
from public.raw_files rf
left join public.document_versions dv on dv.raw_file_id = rf.id
left join public.document_parse_jobs pj on pj.raw_file_id = rf.id
where rf.status in ('stored', 'verified')
group by rf.id, rf.drive_file_id, rf.status, rf.created_at
having count(dv.id) = 0
   and count(pj.id) filter (where pj.status in ('queued', 'leased', 'succeeded')) = 0;

-- V08. Failed workflow runs in last seven days.
-- Purpose: operational error visibility.
-- Expected: reviewed/owned failures only; no unexplained failure.
-- Fail action: create incident/CAPA, link execution ID and retry decision.
select workflow_name, workflow_id, execution_id, status, retry_count,
       error_message, started_at
from public.workflow_runs
where status in ('failed', 'dead_letter')
  and started_at >= now() - interval '7 days'
order by started_at desc;

-- V09. Generated documents without matching audit event.
-- Purpose: every draft/review/approval must be auditable.
-- Expected: zero rows.
-- Fail action: do not synthesize backdated event; investigate writer transaction.
select gd.id, gd.title, gd.status, gd.created_at
from public.generated_docs gd
where not exists (
  select 1
  from public.audit_log al
  where al.details ->> 'generated_doc_id' = gd.id::text
     or al.document_id = gd.id
);

-- V10. Glossary terms used/active but not approved.
-- Purpose: production query rewrite uses only SME-approved terms.
-- Expected: zero active unapproved rows.
-- Fail action: exclude from production profile and send to glossary review.
select id, term_en, term_vi, domain, status, approved_by, approved_at
from public.glossary_terms
where status = 'approved'
  and (approved_by is null or approved_at is null);

-- V11. document_access RLS/policy coverage.
-- Purpose: prove table and policies exist.
-- Expected: rowsecurity=true and at least SELECT/manage policy as designed.
-- Fail action: HOLD all user-facing document search.
select c.relname as table_name, c.relrowsecurity, c.relforcerowsecurity,
       count(p.policyname) as policy_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_policies p
  on p.schemaname = n.nspname and p.tablename = c.relname
where n.nspname = 'public' and c.relname = 'document_access'
group by c.relname, c.relrowsecurity, c.relforcerowsecurity;

-- V12. Failed eval results.
-- Purpose: list release-regression failures with dataset/profile lineage.
-- Expected: zero unresolved failures for a GO candidate.
-- Fail action: HOLD release; open eval_failure/CAPA or approved waiver.
select er.id, er.run_id, er.question_id, er.passed, er.raw_json,
       ef.failure_type, ef.severity, ef.status
from public.eval_results er
left join public.eval_failures ef on ef.eval_result_id = er.id
where er.passed is false
order by er.id;

-- V13. Duplicate canonical discovered URL.
-- Purpose: verify source dedup/idempotency.
-- Expected: zero duplicate active logical items per source.
-- Fail action: merge/reject duplicates; fix canonicalization key.
select source_registry_id, canonical_url, count(*) as duplicates
from public.source_discovered_items
where status <> 'rejected'
group by source_registry_id, canonical_url
having count(*) > 1;

-- V14. Duplicate content SHA-256 across versions.
-- Purpose: detect duplicate version creation.
-- Expected: duplicates only with documented cross-source equivalence.
-- Fail action: mark duplicate/alias; do not create another current version.
select content_sha256, count(*) as versions,
       array_agg(id order by created_at) as version_ids
from public.document_versions
where content_sha256 is not null
group by content_sha256
having count(*) > 1;

-- V15. Citation grounding rate.
-- Purpose: measure percent of answered queries with at least one grounded source.
-- Expected: release threshold >= 95% on answerable eval slice; production is trend.
-- Fail action: HOLD release, inspect retrieval/citation writer/prompt/evaluator.
select
  count(*) filter (where answered) as answered_queries,
  count(*) filter (where answered and has_grounded_source) as grounded_queries,
  round(
    100.0 * count(*) filter (where answered and has_grounded_source)
    / nullif(count(*) filter (where answered), 0),
    2
  ) as grounding_rate_pct
from (
  select q.id,
         q.answer_text is not null and btrim(q.answer_text) <> '' as answered,
         bool_or(coalesce(s.grounded, false)) as has_grounded_source
  from public.ai_queries q
  left join public.ai_query_sources s on s.query_id = q.id
  group by q.id, q.answer_text
) x;

-- V16. Current-version consistency.
-- Purpose: current pointer must reference same logical document and approved version.
-- Expected: zero rows.
-- Fail action: HOLD search/version cutover and reconcile pointer transaction.
select d.id as document_id, d.current_version_id, dv.document_id as version_document_id,
       dv.approved_for_ai_use, dv.superseded_by_version_id
from public.documents d
left join public.document_versions dv on dv.id = d.current_version_id
where d.current_version_id is not null
  and (
    dv.id is null
    or dv.document_id <> d.id
    or dv.approved_for_ai_use is not true
    or dv.superseded_by_version_id is not null
  );

-- V17. Append-only policy/grant red flags.
-- Purpose: list UPDATE/DELETE/TRUNCATE grants on evidence tables to app roles.
-- Expected: zero rows for anon/authenticated/service_role unless explicitly
-- constrained by immutable append function and approved design.
-- Fail action: revoke grants/add guard trigger/retest mutation denial.
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in (
    'audit_log', 'retrieval_log', 'retrieval_candidates',
    'query_rewrite_log', 'tool_call_log'
  )
  and grantee in ('anon', 'authenticated', 'service_role')
  and privilege_type in ('UPDATE', 'DELETE', 'TRUNCATE')
order by table_name, grantee, privilege_type;
