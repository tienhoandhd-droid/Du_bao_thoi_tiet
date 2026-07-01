# Supabase Master Schema Plan

**Project:** `bdttccztjtrcaztjgkot`

**Trạng thái:** design contract; SQL draft tại `supabase/schema-contracts/`, không
được apply trực tiếp.

## 1. Quy ước chung

- Primary key UUID; timestamp `timestamptz`.
- `created_at` cho mọi event/entity; `updated_at` chỉ cho mutable entity, không
  thêm vào append-only log chỉ để “đủ mẫu”.
- Status dùng enum/check constraint; không nhận string tùy ý.
- Mọi bảng exposed schema bật RLS; service/backend policy vẫn least privilege.
- Audit/retrieval/tool/eval event không update/delete trong application path.
- Hash SHA-256 64 hex lowercase với check constraint khi non-null.
- JSONB chỉ dùng cho payload biến thiên; identity/FK/status/metric chính phải là
  typed columns.
- Không tạo bảng khi chưa có writer, reader và test record/fixture.

## 2. Master table matrix

### 2.1 Source/Crawl

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `source_registry` | Canonical source/license policy | domain, mode, trust, owner, active | P0 | WF-09/admin change | WF-09/11/14, dashboard | Yes | domain/mode/active | Low after migration | FDA allow, ISPE deny |
| `license_rules` | Versioned content/license decision | source_id, content_pattern, decision, effective | P0 | governance workflow/manual approved RPC | source gate | Yes | source/effective/status | Medium | allow/deny/metadata-only |
| `source_crawl_runs` | Crawl execution summary | source_id, workflow_run_id, status, counts | P0 | crawl capability | dashboard/health | Yes | source/started/status | Medium until crawl | one synthetic run |
| `source_discovered_items` | URL/item delta queue | run_id, canonical_url, etag, status | P0 | crawl capability | download capability/dashboard | Yes | unique source+URL/hash | Medium | duplicate/change fixtures |
| `raw_files` | Drive/raw lineage | item_id, drive_file_id, binary hash, status | P0 | WF-10 | parse worker/WF-01 | Yes | hash/drive/status | Low after raw test | one synthetic text/PDF metadata |

Legacy mapping: migrate `web_sources` + `approved_sources` to `source_registry`;
map `gdrive_sources` to `raw_files`; retain `drive_sync_log` as operational event
until `workflow_runs` coverage is complete.

### 2.2 Document lifecycle

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `documents` | Logical document/current pointer | code, title, current_version_id, access | P0 existing | ingest/classify/approve | search/frontend | Yes | code/current/type | None | existing 12 |
| `document_versions` | Immutable source/parse/version evidence | document_id, label, hashes, parse, AI approval | P0 new | parse/classify/approve | retrieval/citation/review | Yes | doc+version/hash/status | Low after backfill | 12 legacy versions |
| `document_chunks` | Searchable units | version_id, chunk_index, page/section/hash/vector | P0 existing | chunk/embed | retrieval/citation | Yes | version, GIN, HNSW | None | existing 65 + fixtures |
| `document_access` | User/role/department grants | document_id, principal, rights, expiry | P0 existing | admin/QA | RLS/search/frontend | Yes | doc/user/role/expiry | High currently | two-user allow/deny |
| `document_parse_jobs` | Parse lease/retry/dead-letter | raw_file_id, version_id, parser, status, attempts | P0 new | ingest enqueue/Docling worker | health/WF-01 | Yes | status/lease/idempotency | Low after parse test | success/partial/fail |
| `document_classifications` | Versioned taxonomy decisions | version_id, class, confidence, approved | P0 | classifier/reviewer | search/filter/dashboard | Yes | version/class/status | Medium | regulatory/internal samples |
| `document_tags` | Controlled many-to-many tags | document/version, tag type/value | P0 | classifier/reviewer | retrieval/frontend | Yes | tag/value/doc | Medium | equipment/GMP tags |

Legacy `ingest_jobs` is migrated/deprecated after `document_parse_jobs` cutover.
`documents.version`/file fields remain compatibility columns until every writer and
reader uses `document_versions`.

### 2.3 Retrieval/RAG

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `glossary_terms` | Approved VI–EN terms | term_en/vi, synonyms, status, version | P0 | glossary reviewer | WF-02/query rewrite | Yes | normalized terms/domain | Low after seed | ≥100 core terms target |
| `prompt_versions` | Immutable approved prompts | name, version, body/hash, active | Existing P0 | GitHub release/admin | AI workflows/eval | Yes | unique name+version | None | existing 5 |
| `query_rewrite_log` | Original→expanded evidence | query_id, prompt/glossary version, output, status | P0 | WF-02 | eval/auditor | Yes | query/time/status | Low after search test | VI→EN fixture |
| `retrieval_log` | Retrieval run summary | query_id, profile, mode, counts, latency | P0 | WF-02/12/13 | audit/eval/dashboard | Yes | query/profile/time | Low after search test | hybrid/no-source |
| `retrieval_candidates` | Candidate score breakdown | retrieval_id, chunk_id, ranks/scores/selected | P0 | retrieval append RPC | eval/auditor | Yes | retrieval/rank/chunk | Low | FTS/vector overlap |
| `ai_queries` | User query/answer record | user, query, model/prompt/retrieval, response | Existing P0 | AI workflows | user/auditor/frontend | Yes | user/time/session | High currently | positive/no-source |
| `ai_query_sources` | Claim/citation mapping | query, chunk, version, claim, grounded/rank | Existing P0 | citation validator | frontend/eval/auditor | Yes | query/rank/chunk | High currently | grounded/ungrounded |

`glossary` becomes compatibility view/table during cutover. `retrieval_log` is
canonical run-level name; detailed candidates stay normalized rather than one
large JSON blob.

### 2.4 Agent/tool/audit

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `audit_log` | ALCOA+ audit events | actor, action, target, hashes/details, time | Existing P0 | approved append function | auditor/dashboard | Yes | time/action/target | None | append/mutation-deny |
| `tool_call_log` | Tool invocation evidence | query/session, tool/version, hashes, status, duration | P0 before agent | WF-12/13/tools | auditor/eval | Yes | session/query/tool/time | High until agent gate | allowed/denied/error |
| `agent_sessions` | Controlled agent session state | user, purpose, policy version, status | P1 | WF-12/13 | user/auditor | Yes | user/status/time | High if agent held | canary only |
| `agent_memory_summary` | Optional non-audit summary | session, summary, source message range | P2 optional | controlled summarizer | agent/user | Yes | session/version | Very high | only if used |

Không tạo `agent_memory_summary` trong P0 nếu chưa có consumer. `chat_memory` và
`session_messages` không phải audit log.

### 2.5 Generated documents

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `generated_docs` | Generic DRAFT identity | type, title, source_query, status, prompt/model | P0/P1 | WF-03 | frontend/reviewer | Yes | creator/status/type | Low after UAT | URS/RA/SOP-review drafts |
| `generated_doc_sections` | Structured section content | doc_id, section key/order/content, source IDs | P1 | WF-03 | frontend/reviewer/export | Yes | doc/order | Medium | 3-section draft |
| `doc_reviews` | Review decision history | doc_id, reviewer, status, comment, time | P0/P1 | WF-04/07 | frontend/auditor | Yes | doc/time/status | Low after UAT | request/change/approve |
| `doc_review_findings` | Structured findings | review_id, severity, location, evidence | P1 | WF-04/reviewer | frontend/auditor | Yes | review/severity | Medium | critical/major/minor |
| `approved_doc_snapshots` | Immutable approved PDF/hash | doc_id, review_id, drive ID, SHA-256 | P1 | approval workflow | auditor/download | Yes | doc/hash/time | High before approval | synthetic snapshot metadata |

Legacy protocol tables are empty and can be migrated to generic tables with
compatibility views before any production data is created.

### 2.6 Eval

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `eval_datasets` | Dataset/corpus version | name, version, file/hash, status | P0 | GitHub release/eval RPC | eval/CI/auditor | Yes | unique name+version | Low | current 100-Q dataset |
| `golden_questions` | Expected behavior/source | dataset_id, category, question, expected | Existing P0 | seed/reviewer | eval | Yes | dataset/category/active | None | existing 100 |
| `eval_runs` | Reproducible run | dataset/profile/prompt/model/Git SHA/status | Existing P0 | eval runner | CI/dashboard | Yes | started/status/version | None | existing + v2 run |
| `eval_results` | Per-question metrics | run/question/scores/pass/details | Existing P0 | eval runner | CI/dashboard | Yes | run/question/pass | None | existing 580 |
| `eval_failures` | Normalized failure/CAPA | result, type, severity, owner, status | P0 | eval classifier/reviewer | tracker/dashboard | Yes | status/type/owner | Medium | one negative fixture |

### 2.7 Equipment validation

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `equipment_registry` | Equipment master | code/type/vendor/model/status | Existing P0 | admin | WF-03/05/13/frontend | Yes | unique code/type/status | None | existing 2 |
| `equipment_relationships` | Equipment/system graph | from/to/type/evidence version | P2 | reviewer/import | copilot/search | Yes | endpoints/type | High | defer until consumer |
| `equipment_documents` | Explicit equipment↔version link | equipment, version, relation, active | P1 | classifier/reviewer | search/copilot | Yes | equipment/version/type | Medium | one manual link |
| `validation_templates` | Versioned template | code/type/version/content/status | Existing P0 | template admin | WF-03/13 | Yes | code/version/status | None | existing 3 |
| `validation_tasks` | Controlled task/work item | session/equipment/template/status/owner | P1 | frontend/WF-13 | dashboard/copilot | Yes | owner/status/equipment | Medium | one canary task |
| `validation_outputs` | Draft/output with evidence | task, generated doc, retrieval run, status | P1 | WF-13 | reviewer/frontend | Yes | task/status | Medium | one cited draft |

### 2.8 Dashboard/GitHub integration

| Table | Purpose | Key columns | Req. | Writer | Reader | RLS | Index | Empty risk | Test data |
|---|---|---|:---:|---|---|:---:|:---:|---|---|
| `system_health_metrics` | Time-series health/capacity | metric, value, labels, measured_at | P0/P1 | WF-08/health script | dashboard | Yes | metric/time | Low after collector | corpus/latency metrics |
| `workflow_runs` | n8n execution summary | workflow/execution/status/retry/times | Existing P0 | all workflows via helper | dashboard/auditor | Yes | workflow/status/time | High currently | success/failure/retry |
| `release_notes` | Released artifact summary | version, Git SHA, manifest hash, decision | P1 | release process | dashboard/auditor | Yes | version/time | Medium | one synthetic release |
| `change_requests` | Change-control entity | type/reason/risk/status/approvals | Existing P0 | UI/governance | dashboard/release | Yes | status/time/type | High currently | one draft request |
| `progress_chat_tracker` | Optional DB mirror of GitHub tracker | chat key, status, commit, checkpoint | P1 | sync script | dashboard | Yes | chat/status | High | only after sync exists |

GitHub Markdown remains canonical for progress. Không tạo
`progress_chat_tracker` live trước khi có writer sync và dashboard reader.

## 3. Required constraints/index/RLS patterns

### Immutable/versioned records

- Unique `(document_id, version_label)`.
- Unique non-null `(source_registry_id, content_sha256)` khi phù hợp.
- `superseded_by_version_id <> id`.
- Approved version yêu cầu reviewer/approved_at.
- Current pointer phải trỏ version cùng document.

### Parse/index jobs

- Unique idempotency key.
- Attempts `0..max_attempts`.
- Lease required khi status `leased`.
- Failed/dead-letter error summary không chứa secret/raw payload.

### Citation

- Grounded citation yêu cầu `chunk_id` và `document_version_id`.
- Citation version phải trùng chunk version.
- Citation chỉ được append cho query do caller sở hữu hoặc backend hẹp.

### Append-only

`audit_log`, `retrieval_log`, `retrieval_candidates`, `query_rewrite_log`,
`tool_call_log`, review history và eval evidence không có application
UPDATE/DELETE policies. Trigger guard nếu owner/backend path có thể mutate.

## 4. SQL draft và rollback

- Forward draft:
  [`supabase/schema-contracts/p0-master-schema-draft.sql`](../../supabase/schema-contracts/p0-master-schema-draft.sql)
- Rollback/compatibility draft:
  [`supabase/schema-contracts/p0-master-schema-rollback-draft.sql`](../../supabase/schema-contracts/p0-master-schema-rollback-draft.sql)

Hai file là architectural draft, không phải migration 024 và không được apply.
Khi triển khai, tách thành migrations 024–032 theo master plan, review từng file,
chạy test/rollback và xin xác nhận riêng.

## 5. Empty-table prevention gate

Trước khi tạo một bảng trong migration thật phải có đủ:

- ít nhất một named writer workflow/script/RPC;
- ít nhất một named reader workflow/frontend/eval/dashboard;
- test payload/seed path;
- validation query;
- retention/rollback decision;
- owner và phase activation.

Nếu thiếu một mục, trạng thái table là `DESIGN_ONLY`, không tạo live.
