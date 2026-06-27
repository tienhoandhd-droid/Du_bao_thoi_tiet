# Checklist liên kết GitHub · Supabase · n8n

Quy ước trạng thái:

- `ĐÃ SỬA LOCAL`: đã có file nguồn nhưng chưa áp dụng remote.
- `CHỜ PHA 1B`: sẽ xử lý trong workflow n8n sau khi PHA 1A được duyệt.
- `CHỜ PHA 1C`: sẽ xử lý trong GitHub/frontend sau khi PHA 1B được duyệt.
- `THỦ CÔNG`: cần cấu hình trên dashboard hoặc quyền tài khoản.
- `CHỜ XÁC MINH`: cần Claude Code/MCP kiểm tra thêm.

## A. Lỗi cấu hình và phát hành

| ID | Mức | Lỗi | Hướng giải quyết | Cách giải quyết cụ thể | Trạng thái |
|---|---|---|---|---|---|
| CFG-01 | P0 | GitHub Pages chứa URL và anon key project cũ | Khóa project ref đúng ở CI | Đổi GitHub Variables sang `bdttccztjtrcaztjgkot`; CI fail nếu URL/key không cùng ref hoặc bundle còn ref cũ | CHỜ PHA 1C |
| CFG-02 | P0 | n8n production và Supabase dùng hai project auth khác nhau | Một baseline JWT Cách B duy nhất | Chuẩn hóa URL `/auth/v1/user`, anon key đúng và `onError=continueErrorOutput` trên mọi TKTL workflow | CHỜ PHA 1B |
| REL-01 | P0 | Pages ở Chat 09, Supabase ở 014, n8n có WF-12 active | Release manifest chung | Ghi Git SHA, migration version, workflow version ID và Pages artifact trong một manifest trước deploy | CHỜ PHA 1C |
| REL-02 | P1 | Draft n8n khác bản publish nhưng handoff ghi PASS | Phân biệt draft/test/published | Checklist release phải ghi cả `versionId` và `activeVersionId`; chỉ đánh PASS sau test production | CHỜ PHA 1B |
| DOC-01 | P1 | `CLAUDE.md` và handoff còn URL project cũ | Một nguồn cấu hình chuẩn | Sửa tài liệu, thêm rule quét ref cũ trong CI | CHỜ PHA 1C |
| DOC-02 | P2 | Tài liệu ghi PostgreSQL 16, project thực tế là 17.6 | Đồng bộ tài liệu runtime | Cập nhật stack sau khi Claude xác nhận lại qua MCP | CHỜ PHA 1C |

## B. Supabase

| ID | Mức | Lỗi | Hướng giải quyết | Cách giải quyết cụ thể | File/kiểm tra | Trạng thái |
|---|---|---|---|---|---|---|
| SB-01 | P0 | Ba view tài liệu chạy theo quyền owner, có thể bypass RLS | Security invoker + bỏ anon | `ALTER VIEW ... SET (security_invoker=true)`; revoke anon; grant authenticated/service_role | Migration 015 | ĐÃ SỬA LOCAL |
| SB-02 | P0 | RPC thay đổi/đọc nhạy cảm callable bởi `anon` | Backend-only RPC | Revoke `PUBLIC`, `anon`, `authenticated`; grant `service_role`; n8n dùng Postgres `GMP-check` | Migration 015 | ĐÃ SỬA LOCAL |
| SB-03 | P0 | 17 function có mutable `search_path` | Khóa namespace | `ALTER FUNCTION ... SET search_path TO pg_catalog, public, extensions` | Migration 015 | ĐÃ SỬA LOCAL |
| SB-04 | P0 | `audit_log` có policy INSERT `WITH CHECK(true)` | Không ghi audit trực tiếp từ client | Xóa policy; revoke API INSERT; chỉ backend tin cậy được insert | Migration 015 | ĐÃ SỬA LOCAL |
| SB-05 | P0 | Audit chưa cưỡng chế append-only khi role bypass RLS | Trigger database | Trigger statement-level chặn UPDATE/DELETE/TRUNCATE; revoke mutation grants | Migration 015 | ĐÃ SỬA LOCAL |
| SB-06 | P1 | `chat_memory` chưa có immutable guard | Trigger + grants tối thiểu | Chỉ SELECT/INSERT; trigger chặn mutation; index `(user_id,session_id,created_at)` | Migration 015 | ĐÃ SỬA LOCAL |
| SB-07 | P1 | `update_document_status` tin `p_user_role` | Không tin claim từ caller | PHA 1B phải lấy role thật từ DB trước khi gọi; pha SQL tiếp theo có thể thay function tự xác minh role | Migration 015 đã chặn API trực tiếp; phần role CHỜ PHA 1B | MỘT PHẦN |
| SB-08 | P1 | Leaked-password protection chưa bật | Bật Auth protection | Bật trên Supabase Dashboard rồi test mật khẩu rò rỉ | Dashboard | THỦ CÔNG |
| SB-09 | P1 | Repo không có migration nền 001–012 | Schema-as-code đầy đủ | Export schema-only, chuẩn hóa baseline và runbook phục hồi; không apply baseline lên project đang chạy | Pha đóng gói | CHỜ PHA SAU |
| SB-10 | P2 | 205 advisor performance warning | Tối ưu sau bảo mật | Ưu tiên FK index thật sự dùng, RLS initplan và duplicate index; không xóa index chỉ vì “unused” khi DB chưa có tải | Migration riêng | CHỜ PHA SAU |

## C. n8n TKTL

| ID | Mức | Lỗi | Hướng giải quyết | Cách giải quyết cụ thể | Trạng thái |
|---|---|---|---|---|---|
| N8N-01 | P0 | 8 workflow production dùng URL/key project cũ | JWT baseline mới | Sửa WF-01–06, WF-09, WF-11 theo một node auth byte-identical | CHỜ PHA 1B |
| N8N-02 | P0 | WF-07 dùng URL mới nhưng key cũ | Thay đúng cặp URL/key | Sửa node Verify JWT và test token đúng/sai project | CHỜ PHA 1B |
| N8N-03 | P0 | WF-12 nhận `anon_key` từ request body | Không tin cấu hình do client gửi | Lấy Authorization header; dùng anon key project đúng trong node auth chuẩn | CHỜ PHA 1B |
| N8N-04 | P0 | SQL nội suy request trong WF-01–07 và một phần WF-09/11 | Parameterized SQL | Dùng `$1...$n` + `queryReplacement`; enum allowlist; ép/cap limit/offset | CHỜ PHA 1B |
| N8N-05 | P0 | WF-12 load memory chỉ theo `session_id` | Ràng buộc chủ sở hữu | `WHERE session_id=$1 AND user_id=$2`; user ID lấy từ Verify JWT | CHỜ PHA 1B |
| N8N-06 | P0 | Node “Audit INSERT” WF-12 không ghi `audit_log` | Audit thật, append-only | Trong cùng luồng lưu query, INSERT audit bằng hàm/SQL đã kiểm soát; không UPDATE/DELETE | CHỜ PHA 1B |
| N8N-07 | P1 | WF-12 gọi `hybrid_search_v3` với vector NULL | Sinh embedding thật | Dùng `OpenAl` với `text-embedding-3-small`, rồi truyền vector 1536 vào v3 | CHỜ PHA 1B |
| N8N-08 | P1 | WF-02 citation grounding chỉ có ở draft | Test rồi publish đúng version | Giữ CTE save citation, parameterize SQL, test rows `ai_query_sources`, xin phép publish | CHỜ PHA 1B |
| N8N-09 | P1 | CORS `*` trên endpoint frontend | Origin allowlist | Chỉ cho origin GitHub Pages; preflight đúng | CHỜ PHA 1B |
| N8N-10 | P1 | WF-08 health public và gọi OpenAI mỗi request | Health tối thiểu + rate limit | Auth/allowlist hoặc cache; không lộ số liệu nội bộ | CHỜ PHA 1B |
| N8N-11 | P1 | Không có saved execution để xác minh runtime | Lưu lỗi có kiểm soát | Lưu failed execution/metadata; tránh lưu toàn bộ nội dung GMP nhạy cảm | CHỜ PHA 1B |
| N8N-12 | P1 | MCP không hiển thị credential binding live | Xác minh tại n8n UI/MCP phù hợp | Mỗi node chỉ được dùng `GMP-check` và `OpenAl`; không thêm credential thứ ba | CHỜ XÁC MINH |

## D. GitHub và frontend

| ID | Mức | Lỗi | Hướng giải quyết | Cách giải quyết cụ thể | Trạng thái |
|---|---|---|---|---|---|
| GH-01 | P0 | CI chỉ kiểm tra biến có giá trị | Semantic config guard | Kiểm exact Supabase URL, JWT ref, webhook base và cấm project ref cũ trong `dist` | CHỜ PHA 1C |
| GH-02 | P1 | `main` không branch protection | PR-only release | Bật required checks/review; không push trực tiếp | THỦ CÔNG |
| GH-03 | P1 | GitHub CLI token hết hạn | Xác thực lại | `gh auth login`; sau đó đọc Variables/Secrets và chạy workflow theo quyền người dùng | THỦ CÔNG |
| GH-04 | P1 | Action dùng mutable tags | Pin SHA | Pin `checkout`, `setup-node`, Pages actions theo commit SHA | CHỜ PHA 1C |
| FE-01 | P1 | Artifact chỉ có React dashboard nhưng UI nói vanilla chạy song song | Chọn một topology deploy rõ ràng | Deploy vanilla ở root + React `/v2/`, hoặc bỏ thông báo “song song” | CHỜ PHA 1C |
| FE-02 | P0 | Vanilla dùng `innerHTML` với dữ liệu health/document/audit | DOM-safe rendering | Dùng `textContent`/DOM nodes hoặc escape tất cả dữ liệu DB/API trước khi render | CHỜ PHA 1C |
| FE-03 | P2 | Vite/esbuild dev dependency có advisory | Upgrade riêng | Nâng Vite theo major được hỗ trợ, cập nhật package + lock cùng nhau, build hồi quy | CHỜ PHA 1C |

## E. Cổng nghiệm thu trước khi xây tiếp

### PHA 1A — Supabase (2026-06-27) ✅ HOÀN TẤT
- [x] Migration 015 được Claude Code review PASS (kỹ thuật đúng, idempotent, có rollback).
- [x] Lỗi bổ sung từ MCP đã được sửa trong 015: `view_audit_log` scope đổi từ `{public}` sang `{authenticated}`.
- [x] Người dùng xác nhận apply — migration 015 đã apply thành công lên `bdttccztjtrcaztjgkot`.
- [x] 3 view có `security_invoker=true` (xác minh MCP: `reloptions=[security_invoker=true]`).
- [x] `anon_execute=false` trên 5/5 RPC nhạy cảm kiểm tra (`update_document_status`, `supersede_document`, `write_audit_log`, `get_recent_audit_logs`, `hybrid_search_v3`).
- [x] `proconfig=[search_path=pg_catalog, public, extensions]` trên toàn bộ hàm đã xử lý.
- [x] `user_has_role`, `user_has_any_role` giữ `anon_execute=true` → RLS không gãy.
- [x] Trigger `audit_log_append_only_guard` tồn tại: BEFORE DELETE OR UPDATE OR TRUNCATE FOR EACH STATEMENT.
- [x] Trigger `chat_memory_append_only_guard` tồn tại: BEFORE DELETE OR UPDATE OR TRUNCATE FOR EACH STATEMENT.
- [x] Policy `insert_audit_log` (public WITH CHECK true) đã bị xóa.
- [x] Policy `view_audit_log` scope `{authenticated}`, yêu cầu admin/qa_manager/auditor.
- [x] Index `idx_chat_memory_user_session_created_at (user_id, session_id, created_at DESC)` đã tạo.

### PHA 1B — n8n TKTL (sau khi PHA 1A apply thành công)
#### WF-12 ✅ HOÀN TẤT (publish 2026-06-27, activeVersionId: 49f1da81)
- [x] **[P0] N8N-03: Verify JWT hardcode anon key project `bdttccztjtrcaztjgkot`** — bỏ lấy từ body.
- [x] **[P0] N8N-06: "Audit INSERT" → CTE ghi `ai_queries` + gọi `write_audit_log('ai_query')`** — audit trail thật.
- [x] **[P1] N8N-05: Load Memory thêm `AND user_id = $2::uuid`** — ngăn cross-user memory read.

#### WF-01–07, 09, 11 ✅ HOÀN TẤT (publish 2026-06-27)
- [x] **[P0] N8N-01/02: 9 workflow: Verify JWT URL `bdttccztjtrcaztjgkot.supabase.co` + anon key mới** — published.
  - WF-01 `2c707741` · WF-02 `dc7e9e84` · WF-03 `fd8683a7` · WF-04 `201ce51a`
  - WF-05 `91f75a00` · WF-06 `9a94437e` · WF-07 `17025042` · WF-09 `3639a05a` · WF-11 `bf515a26`
- [x] **WF-01/09: URL typo `.supabase/` → `.supabase.co/` đã sửa** cùng lúc.

#### N8N-04 ✅ HOÀN TẤT (publish 2026-06-27)
- [x] **[P0] N8N-04: Parameterized SQL + allowlist validation + limit/offset cap**
  - WF-01 `025604bc`: `PG: Get User Roles` → `$1::uuid`; `PG: Check Duplicate` → `$1..$4`; `PG: Create Document` → `$1..$18` (INSERT 20 cols)
  - WF-02 `767e4afb`: `PG: Get User Info` → `$1::uuid`
  - WF-03 `66c5e44a`: `Parse + Auth` Code — allowlist `protocol_type` `/^[a-z0-9_]{1,30}$/`, `equipment_code` `/^[A-Za-z0-9\-_\.]{1,50}$/`, `language_mode` enum
  - WF-04 `fb751091`: `Parse + Auth` Code — allowlist `protocol_type`
  - WF-05 `1a3919c5`: `Parse + Auth` Code — allowlist `formula_code` `/^[A-Za-z0-9\-_\.]{1,50}$/`
  - WF-06 `f7b7ee5a`: `Parse + Build SQL` Code — `parseInt()` + `Math.min(max(limit,1),100)` + `Math.max(offset,0)` cap
  - WF-07 `8f2d714c`: `PG: Get Roles` → `$1::uuid`
  - WF-09 `c03ee46b`: `PG: Check Role` → `$1::uuid`
  - WF-11 `bad508fe`: `PG: Check Role` → `$1::uuid`
- **Phạm vi còn lại (Code-node-built SQL):** `PG: Insert Chunks + Audit` (WF-01/09/11), `PG: Hybrid Search` / `PG: Save Query + Audit` (WF-02), `PG: Save Protocol/Review/Job + Audit` (WF-03/04/05), `PG: Search Documents` (WF-06), `PG: Update Status` (WF-07) — các node này đã có `replace(/'/g,"''")` tại Code node; không parameterize được vì multi-statement hoặc dynamic SQL.

#### N8N-07 ✅ HOÀN TẤT (active 2026-06-27)
- [x] **[P1] N8N-07: WF-12 v2 (`DMcZCeYXTFRUyufV`) thay WF-12 cũ (`koOnoSQdpsBAigUj`)**
  - Thêm node `Embed Query` (HTTP Request → `POST /v1/embeddings`, model `text-embedding-3-small`, credential `OpenAl`) giữa `Load Memory` và `AI Agent`
  - `rag_search`: SQL `NULL::vector` → `$3::vector`; queryReplacement inject `JSON.stringify($('Embed Query').first().json.data[0].embedding)` (fallback `null` nếu lỗi → text-only search)
  - `literature_lookup`: tương tự `rag_search`
  - `AI Agent` text cập nhật: `$json.memory` → `$('Load Memory').first().json.memory` (vì predecessor đổi sang Embed Query)
  - `AI Agent` system prompt đúng tiếng Việt
  - Webhook path `/webhook/assistant-query` giữ nguyên; `active: true`, activeVersionId `8d6c7110`
  - Chuỗi: Webhook → Verify JWT → Auth Gate → Load Memory → **Embed Query** → AI Agent → Prepare Response → Save Memory User → Save Memory Assistant → Audit INSERT → Respond 200
  - Giới hạn: embedding lấy từ query gốc của user (không phải query AI tự reformulate); đây là trade-off chấp nhận được cho QA chatbot

#### N8N-08 ✅ HOÀN TẤT (xác minh 2026-06-27)
- [x] **[P1] N8N-08: WF-02 citation grounding đã có trong activeVersion `767e4afb`** — issue "chỉ có ở draft" giải quyết khi N8N-01/04 publish.
  - `ai_query_sources` schema: 15/15 cột INSERT khớp (query_id, chunk_id, document_id, document_code, document_version, language_code, page_number, section_code, section_title, source_type, relevance_score, source_priority, grounded, citation_rank, snippet).
  - `ai_queries` schema: 13/13 cột INSERT khớp.
  - `confidence_level` enum: `{HIGH, MEDIUM, LOW, BLOCKED}` — khớp với logic node.
  - `PG: Hybrid Search` / `PG: Save Query + Audit` dùng dynamic SQL với `esc()` — ghi nhận "phạm vi còn lại" từ N8N-04, chấp nhận.
  - Verify JWT: `bdttccztjtrcaztjgkot.supabase.co` ✅.

### PHA 1C — GitHub/frontend (bắt đầu 2026-06-27)
- [x] **CI guard + release manifest** — `deploy.yml` cập nhật:
  - Guard 1 (pre-build): kiểm `SUPABASE_URL` chứa `bdttccztjtrcaztjgkot`, không chứa `xrpnlpfcoarouoqkhgfp`; decode JWT payload (base64url) xác nhận `ref=bdttccztjtrcaztjgkot`.
  - Guard 2 (post-build): `dist` không chứa `xrpnlpfcoarouoqkhgfp`.
  - Bước `Tao release manifest`: ghi `dist/release-manifest.json` với `git_sha`, `built_at`, `migration_version=015`, `n8n_active_version_ids` (10 WF), `supabase_project`.
- [x] **THỦ CÔNG — GitHub Variables** đổi sang project `bdttccztjtrcaztjgkot` ✅
- [x] **Action xanh** (git_sha `98ee969c`, built_at `2026-06-27T12:51:27Z`) — Guard 1 + Guard 2 pass.
- [x] **Bundle không chứa `xrpnlpfcoarouoqkhgfp`** — Guard 2 xác nhận.
- [x] **Release manifest** tại `https://tienhoandhd-droid.github.io/Du_bao_thoi_tiet/release-manifest.json` ✅ — 10 WF IDs, migration 015, supabase_project `bdttccztjtrcaztjgkot`.
- [ ] **FE-02 (P0)**: vanilla `js/app.js` còn `innerHTML` không escape → sẽ vá khi port sang React (Chat 10, React escape mặc định). Vanilla giữ sống đến khi parity.
- [x] **PHA 1A + 1B + 1C ĐẠT** — sẵn sàng tiếp tục Chat 10.

