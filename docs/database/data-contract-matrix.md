# CRAVE Data Contract Matrix

Mục tiêu của matrix là bảo đảm mỗi capability có input/output typed, table/cột
nhận dữ liệu, error/retry/audit path và test payload. Tên capability không renumber
workflow TKTL live.

## 1. Contract rules

- JWT-derived identity lấy từ verified `/auth/v1/user`, không tin body/user ID tự gửi.
- User-facing retrieval gọi typed RPC qua user JWT/RLS, không owner SQL.
- Write workflow gọi parameterized RPC/query, không nối raw content thành SQL.
- Mỗi write có idempotency/correlation/workflow run.
- Mỗi error có sanitized code/summary, không log secret/raw regulated content.
- Mọi AI output ghi prompt/model/retrieval/dataset version phù hợp.
- Mọi citation ghi immutable document version + chunk.

## 2. Capability contract matrix

| Capability / implementation | Trigger + main nodes | Input | Output | Tables + columns written | Required/NOT NULL | Failure/retry/stop | Audit + dashboard | Test payload |
|---|---|---|---|---|---|---|---|---|
| Source monthly crawl / WF-09 refactor + future scheduler | Schedule/manual → registry RPC → HTTP sitemap/feed → normalize/dedup | active source ID, run config | discovered canonical items | `source_crawl_runs(source_id,workflow_run_id,status,started_at)`; `source_discovered_items(run_id,source_id,canonical_url,status,discovered_at)` | source/run/URL/status | retry network 3x with backoff; stop unknown/deny/expired policy | `workflow_runs`; audit `source_crawl`; health failed/items counts | `n8n/test-payloads/source-crawl.json` |
| Raw download/Drive / WF-10 | queue/webhook → JWT/admin gate → HTTP/Drive upload → complete RPC | discovered item + allowed rule | Drive ID, size, binary hash/status | `raw_files(source_item_id,drive_file_id,file_name,mime_type,binary_sha256,status,created_at)`; `drive_sync_log` compatibility | item/file/hash/status | retry transient; stop MIME/size/hash/policy mismatch | workflow run + `raw_file_stored` | `raw-file-download.json` |
| Docling parse / WF-01 + local worker | queued parse job → lease → Docling → validate quality → complete | raw_file_id, expected hash, parser config | structured MD/JSON metadata, parse score | `document_parse_jobs(raw_file_id,status,parser_name,parser_version,attempts,...)`; `document_versions(parse_status,parse_quality_score,parsed_at,content_sha256)` | raw/job/status/parser | retry parse timeout; stop hash mismatch; dead-letter after max | workflow/job metrics + `document_parse` audit | `docling-parse-job.json` |
| Metadata/classification / WF-01/09/11 | parsed version → rule classifier → optional OpenAI → reviewer | version content/metadata/source | typed class/tags/proposed title | `document_classifications(document_version_id,class_key,class_value,confidence,status)`; `document_tags(document_id,document_version_id,tag_type,tag_value)`; logical `documents` current snapshot after approval | version/class/status | model failure falls back rules/review; no auto approval | `document_classify` audit, needs-review metric | `classification.json` |
| Chunk + embedding / WF-01 + future WF-15 | approved parse → chunker → OpenAl embeddings → transactional write | version ID, structured content, profile | chunks/index readiness | `document_chunks(document_version_id,content,chunk_index,page/section,chunk_sha256,token_count,embedding,embedding_model,status)`; `document_parse_jobs/index job`; version index status | version/content/index/hash/model/status | count/dimension/hash mismatch stops; idempotent retry | `document_index` audit, missing embedding metric | `chunk-embed.json` |
| Metadata search / WF-06 | webhook → Verify JWT → validate filters → `search_documents_v1` | JWT + typed filters/page | permitted logical/current versions | read only; `workflow_runs`; optional audit query summary | JWT/filter contract | no retry auth/validation; retry transient once | denied/error security event; latency metric | `document-search.json` |
| Bilingual RAG search / WF-02 | webhook → Verify JWT → glossary/rewrite → embedding → `hybrid_search_v4` | JWT, query, filters, session | retrieval ID + selected chunks/scores | `ai_queries(user_id,query_text,query_normalized,query_expanded,prompt/model/retrieval...)`; `query_rewrite_log`; `retrieval_log`; `retrieval_candidates` | user/query/profile/status/time | fallback deterministic glossary/original; stop no permission/invalid embedding; FTS-only mode explicit | `ai_query` audit + latency/no-source metrics | `rag-query.json` |
| Citation answer / WF-02 | selected chunks → versioned prompt → OpenAI → claim validator → response | retrieval ID + selected chunk IDs | answer VI, claims/citations/confidence | `ai_queries(answer_text,confidence,tokens,processing_time,error)`; `ai_query_sources(query_id,chunk_id,document_version_id,claim_text,grounded,citation_rank)` | query/grounded/chunk/version for grounded claim | malformed JSON/no-source → refuse; generation retry at most once | audit answer hash/source IDs, citation-rate metric | `citation-answer.json` |
| Google Docs DRAFT / WF-03 refactor | authenticated request → fetch retrieval evidence/template → OpenAI → Google Docs create | query/retrieval/template/equipment | Google Doc DRAFT + sections | `generated_docs(type,title,google_doc_id,status='draft',source_query_id,prompt/model/template...)`; `generated_doc_sections`; `workflow_runs` | creator/type/title/status/source | stop insufficient citation; retry Drive transient; never auto approve | `generated_doc_create` audit + draft metric | `generated-doc-draft.json` |
| Review/approval / WF-04 + WF-07 | reviewer action → role gate → findings/status RPC → optional snapshot | generated doc/review payload | review history/current status/snapshot | `doc_reviews`; `doc_review_findings`; `approved_doc_snapshots`; version/current pointer for source docs only via separate gate | doc/reviewer/status/time | optimistic lock; invalid transition stops; no model auto-approve | review/approve audit + pending metric | `doc-review.json` |
| Eval runner / GitHub Actions + scripts | PR/manual/schedule → fixed dataset/profile/corpus | dataset version, release candidate | run/results/failures/report | `eval_runs(dataset/profile/model/git/workflow/status)`; `eval_results`; `eval_failures` | dataset/run/model/git/status | fail gate on leakage/threshold; rerun new run, never overwrite | release gate report + eval metrics | `eval/datasets/retrieval-v4.jsonl` |
| Dashboard collector / WF-08 | schedule/GET → health RPC/read metrics → append | metric allowlist/window | health summary | `system_health_metrics(metric_name,numeric_value,labels,measured_at)`; `workflow_runs` | metric/value/time | skip unsupported metric; retry read transient | alert/security event on critical | `health-collector.json` |
| Controlled agent / WF-12 | webhook → Verify JWT → policy/session → allowlisted tools → citation validator | JWT, purpose, user message | cited answer/tool history | `agent_sessions`; `session_messages`; `tool_call_log`; `ai_queries/sources`; `audit_log` append | user/policy/status/tool/status/time | no free HTTP/SQL; stop denied tool/no source; bounded tool count | tool/audit/retrieval metrics | `controlled-agent.json` |
| Validation Copilot / WF-13 after gate | webhook → Verify JWT → equipment/template context → retrieval tool → draft output | equipment, IQ/OQ/PQ, query | cited draft/checklist | `validation_sessions`; `session_messages`; `validation_tasks`; `validation_outputs`; tool/query/source logs | user/equipment/type/status | stop invalid equipment/type/no source; bounded tools | validation/audit metrics | `validation-copilot.json` |
| External web discovery / WF-14 | webhook → Verify JWT → Tavily → label unverified | query/mode | unverified web candidates | `workflow_runs`; audit summary; optionally `source_discovered_items` only after explicit submit/review | user/query/status | no automatic corpus insert; retry Tavily transient | `web_search` audit, external-source metric | `web-search.json` |

## 3. Current TKTL coverage

| Workflow | Current reads/writes | Target contract | Main gap/status |
|---|---|---|---|
| WF-01 Document Ingest | roles/documents/chunks/audit via owner SQL | parse/version/chunk/index jobs | P0 refactor; raw decode/dynamic SQL |
| WF-02 RAG Query | user info/prompts/v3/query/audit | rewrite/retrieval/citation contracts | P0 refactor; owner search/LLM rerank |
| WF-03 Draft Protocol | templates/documents/generated protocol | generic generated docs/sections | Upgrade after retrieval gate |
| WF-04 Check Protocol | protocol review/findings | generic doc reviews/findings | Upgrade after generated-doc contract |
| WF-05 Calculation Helper | formula/jobs/audit | retain; link generated output if used | Not core search P0 |
| WF-06 Document Search | raw `documents` SELECT | `search_documents_v1` invoker | **P0 immediate** |
| WF-07 Approve Document | document update/audit | immutable version/current pointer/review | P0 version gate |
| WF-08 Health Monitor | direct health queries | corpus/workflow/retrieval metrics | P0/P1 collector |
| WF-09 Web Source Ingest | raw fetch/doc/chunk/audit | registry/discovery/raw/version/parse jobs | P0 source gate |
| WF-10 Google Drive Sync | Drive + sync log | raw file/idempotency/parse enqueue | P0 raw lineage |
| WF-11 Literature Search | Europe PMC + doc/chunk ingest | registry/license/version/index | P0 source gate |
| WF-12 QA Assistant | owner Postgres tools/memory/audit | controlled agent/tool/retrieval logs | HOLD until eval gate |
| WF-13 Validation Copilot | owner tools/session/audit | controlled retrieval/tasks/outputs | HOLD until eval gate |
| WF-14 Web Search | Tavily + audit | discovery only/unverified boundary | PASS direction; no auto ingest |
| Future WF-15 Reindex | none | index job batch worker | New inactive/manual |

## 4. Write-time requirements

### Every workflow run

Write or finalize `workflow_runs` with:

```text
workflow_name, workflow_id, execution_id, status,
input_summary, output_summary, retry_count,
started_at, completed_at, triggered_by
```

Input/output summary must be sanitized and bounded.

### Every AI workflow

Must link:

```text
model_used
prompt_version_id/version
retrieval profile/run when retrieval occurs
tokens/latency where available
query/session/user identity
error/no-source outcome
```

### Every data-producing workflow

- deterministic idempotency key;
- transaction/RPC boundary where partial state is unsafe;
- success verification query;
- error/retry/dead-letter path;
- append audit event for regulated state changes.

## 5. Planned test payload files

The paths above are contracts. Files are created with each implementation Chat,
not as empty placeholders. Before workflow update, matching payload file must exist
and contain at least:

- positive case;
- missing/invalid JWT;
- validation failure;
- permission denial;
- transient backend failure/retry;
- duplicate/idempotent replay when workflow writes.
