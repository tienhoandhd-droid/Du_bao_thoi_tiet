# S1 Supabase read-only evidence — 2026-06-29

**Project:** `bdttccztjtrcaztjgkot`
**Method:** `psql` qua Supabase Shared Pooler, environment local ngoài repo
**Database user observed:** `postgres`
**Mode:** SELECT-only; các query pack chạy trong `BEGIN READ ONLY`
**Decision:** **VERIFIED — HOLD**

## 1. Scope

Evidence này được tạo để đóng phần “không có Supabase live verification” của
System Check S1. Không có `apply_migration`, không có DDL/DML, không có n8n
mutation, không ghi dữ liệu Supabase.

Mật khẩu/connection string không được ghi vào repo. Vì DB password đã từng bị đưa
vào chat, cần rotate/reset sau khi hoàn tất remediation.

## 2. Migration live

Live `supabase_migrations.schema_migrations` có 12 records:

| Version | Name |
|---|---|
| `20260627012519` | `013_citation_grounding` |
| `20260627024207` | `014_chat_memory` |
| `20260627110302` | `015_platform_security_hardening` |
| `20260627200153` | `017_equipment_glossary` |
| `20260627204445` | `018_seed_validation_data` |
| `20260628013552` | `019_drive_sync_log` |
| `20260628070328` | `020_validation_sessions` |
| `20260628112355` | `021_eval_harness` |
| `20260628113034` | `021b_eval_function_v2` |
| `20260628113529` | `021c_eval_function_v3_or_tsquery` |
| `20260628113613` | `021d_eval_score_columns_fix` |
| `20260628125753` | `022_fix_eval_rank_order` |

Findings:

- Live head tới `022`.
- Live không có migration `016`; source `016_eval_harness.sql` vẫn là drift lịch sử.
- Live `021c` tên là `021c_eval_function_v3_or_tsquery`, trong khi source file là
  `021c_eval_function_v3.sql`. Đây là name drift đã được S1 dự đoán và nay đã xác minh.

## 3. RLS state

| Table | RLS enabled | FORCE RLS | Owner |
|---|---:|---:|---|
| `audit_log` | true | false | `postgres` |
| `document_chunks` | true | false | `postgres` |
| `documents` | true | false | `postgres` |
| `eval_results` | true | false | `postgres` |
| `eval_runs` | true | false | `postgres` |

Findings:

- RLS đã bật cho các bảng critical đã kiểm.
- `FORCE RLS` đang false cho tất cả bảng. Nếu automation/credential dùng table
  owner hoặc role bypass RLS, RLS không phải boundary đủ.

## 4. Policies and grants

### 4.1 Audit log

Live policies/grants:

- `audit_log` policy duy nhất: `view_audit_log` cho `authenticated` SELECT với
  role `admin`, `qa_manager`, `auditor`.
- Non-owner grants:
  - `authenticated`: SELECT.
  - `service_role`: INSERT, REFERENCES, SELECT, TRIGGER.
  - Không thấy UPDATE/DELETE/TRUNCATE grant cho `authenticated` hoặc `service_role`.
- Triggers:
  - `audit_log_append_only_guard` BEFORE UPDATE.
  - `audit_log_append_only_guard` BEFORE DELETE.
  - Cả hai gọi `crave_block_append_only_mutation()`.

Conclusion: audit append-only control có evidence tốt ở mức live DB cho non-owner
roles. Owner `postgres` vẫn có quyền owner/superuser theo bản chất DB.

### 4.2 Documents/document_chunks/eval tables

Live grants cho `documents`, `document_chunks`, `eval_runs`, `eval_results` còn
rộng ở table-grant level, gồm nhiều quyền cho `anon`/`authenticated`. RLS policies
là control chính để chặn thực thi theo user.

Finding: đây không tự động là leak nếu RLS/policies đúng, nhưng là risk cho các
workflow dùng Postgres credential owner/bypass. Riêng WF-06 cần giữ HOLD vì nó
query trực tiếp `documents` qua Postgres node và credential binding/user chưa được
live-verified.

## 5. Function security

| Function | Security definer | Volatility | Owner | Config/search_path | Execute exposure | Finding |
|---|---:|---|---|---|---|---|
| `hybrid_search_v3(...)` | true | stable | `postgres` | `search_path=pg_catalog, public, extensions` | `postgres`, `service_role`; `anon/authenticated` false | PASS for checked attributes |
| `run_fts_eval_v1(integer,text,text)` | true | volatile | `postgres` | empty | `anon`, `authenticated`, `service_role`, `postgres` true | **FAIL/HOLD** |
| `crave_block_append_only_mutation()` | false | volatile | `postgres` | `search_path=pg_catalog, public` | `anon`, `authenticated`, `service_role`, `postgres` true | Review/revoke recommended |

Critical finding:

- Source `supabase/migrations/022_fix_eval_rank_order.sql` declares
  `run_fts_eval_v1` with `SET search_path = public, extensions`.
- Live `pg_proc.proconfig` for `run_fts_eval_v1` is empty and
  `pg_get_functiondef` prefix does not show `SET search_path`.
- `run_fts_eval_v1` is `SECURITY DEFINER` and executable by `anon`.

Conclusion: Supabase function gate is **FAIL/HOLD** until `run_fts_eval_v1`
search_path and EXECUTE grants are remediated or formally risk-accepted.

## 6. Rollback 021d risk

Live data:

| Metric | Value |
|---|---:|
| `max(score_mean)` | `96.55` |
| `max(score_min)` | `81.03` |
| `eval_runs_count` | `10` |

Finding:

- Existing `021_down.sql` attempts to restore `eval_runs.score_mean` and
  `score_min` to `numeric(5,4)`.
- Live values exceed `numeric(5,4)` capacity for values above `9.9999`.

Conclusion: automatic rollback of `021d` to `numeric(5,4)` is unsafe with current
live data. `021d` rollback must remain HOLD unless it uses explicit data handling,
manual recovery, or approved no-rollback/risk acceptance.

## 7. S1 decision impact

Supabase read-only verification is no longer blocked. It is completed with
findings:

- Migration live/source drift remains: missing `016`, `021c` name drift.
- `run_fts_eval_v1` live security attributes fail source/security expectation.
- `021d` rollback is unsafe against live data.
- WF-06 DB/RLS boundary remains unresolved because owner/bypass credential risk
  is material.

Therefore Supabase gate changes from:

`BLOCKED / NOT VERIFIED`

to:

**VERIFIED — FAIL/HOLD**
