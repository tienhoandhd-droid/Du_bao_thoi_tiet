# CRAVE GMP AI Platform — System Master Upgrade Plan

**Ngày:** 2026-06-29

**Vai trò:** Codex — kiến trúc sư hệ thống + builder

**Project duy nhất:** Supabase `bdttccztjtrcaztjgkot`

**n8n scope:** chỉ workflow prefix `TKTL` tại `n8n.cpc1hn.com`

**Trạng thái:** **PLAN + DRAFT CONTRACTS ONLY — NOT FOR APPLY**

Tài liệu này mở rộng kế hoạch Retrieval V4 thành master plan liên kết bốn source
of truth: Supabase schema, n8n workflow, GitHub artifact và progress/evidence.

## A. Executive Decision

### A.1. Kế hoạch cũ thiếu gì?

| Thiếu hụt | Evidence hiện tại | Hậu quả |
|---|---|---|
| Schema–workflow contract | Nhiều workflow tự ghép SQL; không có matrix cột writer/reader | Dễ có workflow ghi cột không tồn tại hoặc bảng trống |
| Source/license lifecycle | Có `web_sources`, `approved_sources` nhưng chưa có canonical registry/rule/run/item model | Không chứng minh nguồn nào được crawl/ingest |
| Immutable document version | `document_group_id` gom nhiều mã khác nhau; chưa có `document_versions` | Citation không chứng minh version đã dùng |
| Raw-file lineage | 0/12 document có hash/Drive ID/source URL | Không chống trùng hoặc tái lập parse |
| Parse-quality evidence | 0/65 chunk có page/section; quality chỉ default | Có thể embed nội dung parse lỗi |
| Working vector corpus | 0/65 embedding | `hybrid_search_v3` không phải hybrid thực tế |
| Retrieval/tool observability | Không có retrieval/tool logs; AI query/source đều trống | Không replay claim/tool path |
| Generic generated-doc lifecycle | Các bảng protocol-specific đang trống | Chưa quản lý mọi loại DRAFT/review/snapshot |
| Eval dataset/version/failure model | Có 100 golden Q và results nhưng thiếu dataset/failure/release linkage | Khó tái lập gate |
| Coverage/progress tracker | Thiếu CURRENT_STATUS/NEXT_ACTIONS/matrices | Agent tiếp theo không biết exact next action |

### A.2. Điểm giữ nguyên

- Supabase/Postgres/pgvector là datastore chính; không thêm vector DB.
- Google Drive giữ raw originals; DB chỉ lưu lineage/metadata/chunks/evidence.
- OpenAI là AI trả phí duy nhất; `text-embedding-3-small` 1536 chiều.
- n8n native orchestration; không community node/SQL/HTTP tự do cho agent.
- JWT verify qua `/auth/v1/user`; user-facing search phải giữ user RLS context.
- Audit append-only, prompt/model/dataset/retrieval versioning.
- AI chỉ tạo DRAFT; human review/approval bắt buộc.
- 100 golden questions hiện có là seed cho eval v2.
- 14 workflow live không bị renumber để khớp blueprint mới.

### A.3. Điểm phải sửa

1. Chuyển từ bảng rời rạc sang canonical data model có compatibility mapping.
2. Chuyển `documents` thành logical record và thêm immutable
   `document_versions`.
3. Thay direct owner SQL của WF-06 và retrieval consumers bằng typed RPC/RLS.
4. Tách source discovery, raw-file download, parse, classify, chunk/embed thành
   trạng thái/job có idempotency.
5. Tách retrieval run, candidate, query rewrite, citation và tool call evidence.
6. Tổng quát hóa generated protocol thành generated document + review + snapshot.
7. Bổ sung dataset/failure/release linkage cho eval.
8. Bắt buộc writer/reader/test payload cho mỗi table và workflow.

### A.4. Điểm thêm mới

- Source registry/rules/crawl runs/discovered items/raw files.
- Immutable versions, parse jobs, classifications/tags.
- Retrieval/query rewrite/tool logs.
- Generic generated-doc/review/snapshot model.
- Eval datasets/failures.
- Equipment-document relationship/task/output model.
- Health metrics/release notes/progress mirror.
- GitHub coverage matrices, validation SQL và per-chat tracker.

### A.5. Chưa làm ngay

- Không crawl toàn bộ FDA/EMA/WHO/ICH/PIC/S/ISPE.
- Không thêm Qdrant/Milvus/Weaviate.
- Không local reranker production trước retrieval v4 baseline.
- Không equipment graph/multi-hop P2 trước document/citation foundation.
- Không mở controlled agent cho validated use trước citation/eval gate.
- Không xóa bảng legacy trong P0; chỉ deprecate sau dual-read reconciliation.
- Không apply draft SQL trong `supabase/schema-contracts/`.

### A.6. P0/P1/P2 mới

#### P0 — Corpus, retrieval, evidence và contract foundation

- Repo/progress/coverage trackers.
- WF-06 authorization containment.
- Source registry + license rules.
- Raw file + immutable document versions.
- Docling parse jobs/quality gate.
- Chunk/hash/token/embedding readiness.
- Glossary/query rewrite + hybrid v4 RLS.
- Citation/retrieval/tool evidence.
- Generated DRAFT/review foundation.
- Eval v2 + health/workflow metrics.
- 100% schema/workflow coverage, seed/test payload và rollback evidence.

#### P1 — Operational quality và controlled automation

- Scheduled curated crawl with delta/retry.
- Local multilingual reranker experiment.
- Generic Google Docs templates and approved snapshots.
- Controlled agent canary after P0 gates.
- AI reviewer/coprocessor with tool logs.
- Capacity/backup/restore automation.

#### P2 — Advanced validation intelligence

- Equipment relationship graph and multi-hop retrieval.
- Semantic cache tied to corpus/profile versions.
- Advanced incident/CAPA analytics.
- Multi-environment staging/prod promotion.
- Alternative vector infrastructure only after measured pgvector limit.

## B. Master Schema Decision

Chi tiết nằm tại
[`docs/database/supabase-master-schema-plan.md`](../database/supabase-master-schema-plan.md).

Canonical/legacy mapping bắt buộc:

| Canonical target | Existing table(s) | Decision |
|---|---|---|
| `source_registry` | `web_sources`, `approved_sources` | Migrate/merge; legacy compatibility window |
| `raw_files` | `gdrive_sources`, `drive_sync_log` | Canonical raw lineage; keep sync log as event history |
| `document_parse_jobs` | `ingest_jobs` | New typed parse/index job; migrate compatible fields |
| `glossary_terms` | `glossary` | Rename/migrate; compatibility view because source table empty |
| `generated_docs` | `generated_protocols` | Generalize; existing table empty |
| `doc_reviews` | `protocol_reviews` | Generalize; existing table empty |
| `doc_review_findings` | `protocol_review_findings` | Generalize; existing table empty |
| `workflow_runs` | `workflow_runs` | Reuse/extend |
| `prompt_versions` | `prompt_versions` | Reuse/extend, do not duplicate |
| `audit_log` | `audit_log` | Reuse append-only |
| `change_requests` | `change_requests` | Reuse/extend |
| `validation_templates` | `validation_templates` | Reuse |
| `equipment_registry` | `equipment_registry` | Reuse |
| `golden_questions`, `eval_runs/results` | same | Reuse/extend |

Không drop/rename live table trong cùng bước tạo canonical target. Mỗi mapping cần:

```text
create/additive schema
→ backfill
→ dual-write or compatibility view
→ reconciliation
→ consumer cutover
→ observation window
→ deprecation decision
```

## C. Data Contract Decision

Chi tiết tại
[`docs/database/data-contract-matrix.md`](../database/data-contract-matrix.md).

Các workflow blueprint trong yêu cầu không được dùng để renumber live workflows.
Chúng là capability IDs và được map vào workflow thật:

| Capability | Current/future TKTL implementation |
|---|---|
| Monthly source crawl | WF-09 + future scheduled source-crawl workflow từ WF-15 trở đi |
| Raw download to Drive | WF-10 |
| Docling parse | WF-01 refactor + external/local worker via parse jobs |
| Metadata/classification | WF-01/WF-09/WF-11 refactor |
| Chunk + embedding | WF-01 + future WF-15 reindex |
| Bilingual search | WF-02 + WF-06 metadata RPC |
| Citation answer | WF-02; later WF-12/WF-13 consume same contract |
| Google Docs draft | WF-03 refactor |
| Review/approval | WF-04/WF-07 refactor |
| Eval runner | GitHub Actions + eval scripts; no required active n8n workflow |
| Dashboard metrics | WF-08 refactor |
| Controlled agent | WF-12; WF-13 copilot remains gated |

## D. GitHub Repository Plan

Không tạo repo `crave-gmp-ai` mới. Áp dụng cấu trúc vào repo
`tienhoandhd-droid/Du_bao_thoi_tiet` hiện tại:

```text
Du_bao_thoi_tiet/
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── CURRENT_STATUS.md
├── NEXT_ACTIONS.md
├── docs/
│   ├── architecture/       # target architecture, ADR, master plan
│   ├── database/           # schema/data contracts/SQL explanation
│   ├── governance/         # change control, rollback, policy
│   ├── checkpoints/        # live evidence and system checks
│   ├── progress/           # chat index/status/coverage/blockers
│   └── references/         # approved external references
├── supabase/
│   ├── migrations/         # reviewed forward migrations only
│   ├── rollbacks/          # matching rollback/compatibility SQL
│   ├── seeds/              # test/reference seed, no production secrets
│   ├── tests/              # SQL validation/RLS/contract tests
│   ├── schema-contracts/   # draft SQL + machine-readable contracts
│   └── baseline/           # read-only source/live snapshots
├── n8n/
│   ├── workflows/          # redacted canonical TKTL exports
│   ├── workflow-docs/      # inventory/provenance/version evidence
│   ├── workflow-contracts/ # input/output/table contract
│   ├── test-payloads/      # synthetic negative/positive fixtures
│   └── release-manifest.json
├── prompts/                # versioned prompt families
├── eval/
│   ├── golden-questions/
│   ├── datasets/
│   ├── fixtures/
│   ├── reports/
│   ├── promptfoo/
│   ├── ragas/
│   └── deepeval/
├── scripts/
│   ├── backup/
│   ├── ingest/
│   ├── health-check/
│   ├── export-audit/
│   └── validate-schema/
└── .github/
    ├── workflows/
    ├── ISSUE_TEMPLATE/
    └── pull_request_template.md
```

### Folder ownership/use

| Folder | Tạo bởi | Đọc bởi | DB/workflow linkage | File tối thiểu |
|---|---|---|---|---|
| `docs/architecture` | Architect/builder/reviewer | All agents/owner | toàn hệ thống | master plan, ADR |
| `docs/database` | DB builder | n8n/frontend/reviewer | tất cả schema contracts | schema plan, data matrix |
| `docs/progress` | Chat owner | agent tiếp theo | progress tracker mirror | index/status/blockers/matrices |
| `supabase/migrations` | DB builder | CI/reviewer/operator | live schema | forward SQL |
| `supabase/rollbacks` | DB builder | reviewer/operator | restore/compatibility | matching down SQL |
| `supabase/tests` | DB/test builder | CI/reviewer | RLS/data contracts | validation SQL |
| `supabase/schema-contracts` | Architect | DB/n8n/frontend builders | draft schema | P0 draft + rollback draft |
| `n8n/workflows` | n8n builder | CI/reviewer/operator | workflow source | redacted JSON |
| `n8n/test-payloads` | n8n/test builder | CI/manual tester | webhook contracts | positive/negative fixtures |
| `n8n/workflow-contracts` | Architect/n8n builder | DB/frontend/reviewer | table writer/reader map | contract matrix |
| `prompts/*` | Prompt owner | workflow/eval | prompt_versions | prompt + metadata/hash |
| `eval/*` | Eval owner/CI | release gate/reviewer | eval datasets/runs/results | dataset/report/fixture |
| `scripts/*` | Builder | CI/operator | backup/health/audit | safe scripts + README |

## E. Progress Tracker

Canonical files:

- [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md)
- [`NEXT_ACTIONS.md`](../../NEXT_ACTIONS.md)
- [`docs/progress/CHAT_INDEX.md`](../progress/CHAT_INDEX.md)
- [`docs/progress/CHAT_TEMPLATE.md`](../progress/CHAT_TEMPLATE.md)
- [`docs/progress/DECISION_LOG.md`](../progress/DECISION_LOG.md)
- [`docs/progress/BLOCKERS.md`](../progress/BLOCKERS.md)
- [`docs/progress/DATA_CONTRACT_STATUS.md`](../progress/DATA_CONTRACT_STATUS.md)
- [`docs/progress/SCHEMA_COVERAGE_MATRIX.md`](../progress/SCHEMA_COVERAGE_MATRIX.md)
- [`docs/progress/WORKFLOW_COVERAGE_MATRIX.md`](../progress/WORKFLOW_COVERAGE_MATRIX.md)

Các Chat nâng cấp dùng namespace `UPG-CHAT-01…16` để không ghi đè lịch sử
Chat 01–20 cũ.

## F. Coverage Gates

Schema coverage và workflow coverage không chỉ là tài liệu. Trước mỗi apply:

- column có feature nhưng không writer → `MISSING WRITER`;
- column/table không writer hoặc reader → `UNUSED — remove or justify`;
- workflow cần cột không tồn tại → `MISSING COLUMN`;
- critical table không seed/test data → `NO TEST DATA`;
- critical table không RLS → `FAIL`;
- audit/retrieval/tool table có update/delete path → `FAIL`;
- workflow không export/test payload/error/audit path → `FAIL`.

## G. Validation SQL

Canonical pack:
[`supabase/tests/validate_master_schema.sql`](../../supabase/tests/validate_master_schema.sql).

Mỗi query có purpose, expected result và remediation comment; read-only mặc định.

## H. P0 Implementation Roadmap

| Chat | Topic | Main tables | Current/future workflows | Gate |
|---|---|---|---|---|
| UPG-CHAT-01 | Repo structure + tracker | `progress_chat_tracker` P1 mirror | none | tracker/coverage files parse |
| UPG-CHAT-02 | P0 schema draft/rollback | canonical missing tables | none | schema review, no apply |
| UPG-CHAT-03 | Source registry/license | source registry/rules | WF-09/11/14 | allow/deny tests |
| UPG-CHAT-04 | Raw files/Drive | raw files | WF-10 | hash/idempotency tests |
| UPG-CHAT-05 | Crawl runs/items | crawl runs/items | WF-09 + future scheduler | delta/retry/dedup |
| UPG-CHAT-06 | Docling parse jobs | versions/parse jobs | WF-01 + worker | parse quality gate |
| UPG-CHAT-07 | Metadata/classification | classifications/tags | WF-01/09/11 | taxonomy/approval |
| UPG-CHAT-08 | Chunk/embedding | chunks/index jobs | WF-01/WF-15 | 100% required ready |
| UPG-CHAT-09 | Glossary/query rewrite | glossary/rewrite log | WF-02 | SME approval |
| UPG-CHAT-10 | Hybrid search/RLS | retrieval log/candidates | WF-02/06 | leakage 0/non-regression |
| UPG-CHAT-11 | Citation grounding | query sources/tool logs | WF-02/12/13 | claim↔chunk 100% |
| UPG-CHAT-12 | Google Docs DRAFT | generated docs/reviews | WF-03/07 | auto-approve 0 |
| UPG-CHAT-13 | Audit/tool/retrieval logs | audit/tool/retrieval | all writers | append-only/replay |
| UPG-CHAT-14 | Eval v2 | datasets/runs/results/failures | GitHub eval | thresholds/gate failure fixture |
| UPG-CHAT-15 | Health dashboard | health/workflow runs | WF-08/frontend | stale/failure visibility |
| UPG-CHAT-16 | Controlled agent | agent sessions/tool logs | WF-12/13 | only after Chat 10–15 PASS |

Không apply nhiều Chat trong một approval. Mỗi Chat tạo checkpoint/manifest theo
`docs/checkpoints/search-upgrade/README.md`.

## I. Checklist trước apply production

- [ ] `CURRENT_STATUS.md` và `NEXT_ACTIONS.md` cập nhật.
- [ ] Chat/checkpoint/manifest hiện tại hoàn chỉnh.
- [ ] Schema coverage PASS; không `MISSING COLUMN/WRITER`.
- [ ] Workflow coverage PASS; exported JSON + test payload.
- [ ] Exact forward/rollback SQL reviewed.
- [ ] SQL idempotency/static checks PASS.
- [ ] RLS/grants/function owner/search path PASS.
- [ ] Ít nhất một seed/test record cho critical table mới.
- [ ] Data contract positive/negative/retry/error tests có expected result.
- [ ] Audit/retrieval/tool append-only checks PASS.
- [ ] Source/live drift precheck ngay trước mutation.
- [ ] Secret scan PASS; không log credential material.
- [ ] Release manifest/hashes/eval report cập nhật.
- [ ] Separate approval cho Supabase apply.
- [ ] Separate approval cho n8n update/execute/publish.
- [ ] Separate approval cho git push/PR nếu chưa yêu cầu.

## J. Prompt bàn giao Claude Code review

```text
Bạn là Claude Code reviewer cho CRAVE GMP AI Platform.

Đọc theo thứ tự:
1. CURRENT_STATUS.md
2. NEXT_ACTIONS.md
3. docs/architecture/crave-system-master-plan.md
4. docs/database/supabase-master-schema-plan.md
5. docs/database/data-contract-matrix.md
6. docs/progress/SCHEMA_COVERAGE_MATRIX.md
7. docs/progress/WORKFLOW_COVERAGE_MATRIX.md
8. checkpoint/manifest Chat hiện tại

Xác minh độc lập:
- không tạo table trùng legacy/canonical;
- mọi table có writer, reader, RLS/index/constraint/test data;
- mọi workflow có exact columns, error/retry/audit/test payload;
- immutable document version và citation lineage;
- user-facing retrieval giữ JWT/RLS, không DB owner bypass;
- audit/retrieval/tool logs append-only;
- draft không auto-approve;
- eval/security thresholds và rollback/recovery.

Không apply/update/execute/publish/push. Trả PASS/FAIL/HOLD, findings theo mức độ,
exact file/SQL/workflow patch và điều kiện re-test.
```

## K. Quyết định tiếp theo

R00 baseline đã PASS cho source preparation; toàn hệ thống vẫn HOLD. Công việc
tiếp theo là hoàn thiện package UPG-CHAT-01/02 ở source, sau đó quay lại R01
security boundary migration 024 + WF-06. Không apply draft master schema.
