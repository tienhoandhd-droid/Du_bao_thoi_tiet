# S1 remediation note — 2026-06-29

**Liên quan:** `docs/checkpoints/system-check-S1.md`
**Main hiện tại:** `5fb904a799d9623590ae8ba7fdb9a0087e9ba618`
**Quyết định hiện tại:** **HOLD — chưa GO CYCLE 2**

## 1. Tóm tắt

S1 đã được push lên `main` và CI gate blocker đã được remediation thành công.
Required check `TypeScript Build & Lint` hiện đã được tạo và chạy SUCCESS trên
commit `5fb904a`. Tuy nhiên S1 chưa thể đổi sang GO vì Supabase live verification,
rollback/change-control 013–021d, governance issue state và WF-06 security review
vẫn chưa PASS đầy đủ.

## 2. Evidence CI remediation

| Hạng mục | Evidence | Kết quả |
|---|---|---|
| Commit S1 | `f1ef74f docs(s1): record cycle 1 system check HOLD` | Pushed to `main` |
| Commit CI fix | `5fb904a ci: ensure required TypeScript gate always runs` | Pushed to `main` |
| Required workflow | `CI — TypeScript Build & Lint` | Created on `main` push |
| Run | `28343429940` | SUCCESS |
| Required job | `TypeScript Build & Lint` | SUCCESS |
| Deploy | `28343429927` | SUCCESS |

CI fix đã:

- bỏ `paths` filter để required context luôn được tạo;
- bỏ scanner generic `PLACEHOLDER`;
- chỉ quét unresolved sentinel cấu hình cụ thể;
- chuyển secret scan trong CI sang quiet mode để không echo matched material.

## 3. Governance evidence cập nhật

- `docs/governance/change-register.md` được cập nhật thêm trạng thái Cycle 1,
  PR #3, S1 và CI remediation.
- `kehoach.md §14.2` được cập nhật để Chat 01–05 không còn là “kế hoạch” stale.
- Issue #2 trên GitHub vẫn OPEN và body còn chứa finding cũ về WF-14 trước
  remediation. Chưa update/close issue trong note này vì đó là GitHub remote write
  riêng, cần quyết định owner/policy.

## 4. Supabase read-only verification

**Kết quả:** VERIFIED — FAIL/HOLD.

Evidence chi tiết được ghi tại:

- `docs/checkpoints/s1-supabase-readonly-evidence.md`

Các query đã chạy qua `psql` bằng environment local ngoài repo, trong transaction
`BEGIN READ ONLY`, chỉ SELECT metadata/live state. Không có migration apply,
DDL/DML hoặc mutation Supabase.

Kết luận chính:

- Live migration head tới `022`, nhưng live không có `016` và `021c` live name là
  `021c_eval_function_v3_or_tsquery`, khác source filename.
- RLS bật cho `documents`, `document_chunks`, `audit_log`, `eval_runs`,
  `eval_results`, nhưng `FORCE RLS` false và owner là `postgres`.
- `audit_log` có trigger append-only guard cho UPDATE/DELETE; non-owner grants
  không có UPDATE/DELETE/TRUNCATE cho `authenticated`/`service_role`.
- `hybrid_search_v3` có `SECURITY DEFINER` và search_path locked
  `pg_catalog, public, extensions`; execute không mở cho `anon/authenticated`.
- `run_fts_eval_v1` live là `SECURITY DEFINER` nhưng không có search_path config,
  trong khi source `022` có `SET search_path = public, extensions`; function còn
  executable bởi `anon`.
- Live `eval_runs` có `max(score_mean)=96.55` và `max(score_min)=81.03`, nên rollback
  `021d` về `numeric(5,4)` là không an toàn.

## 5. Rollback/change-control 013–021d

**Kết quả:** HOLD.

Tài liệu change-control đã lập:

- `docs/governance/rollback-change-control-013-021d.md`

Kết luận chính:

- không bịa rollback lịch sử;
- `013`–`021` có rollback theo convention cũ nhưng cần canonical hóa;
- `021b`, `021c`, `021d` chưa có rollback riêng;
- `022` rollback hiện là manual restore vì thiếu old function definition;
- cần Supabase read-only evidence trước khi đóng blocker.

## 6. WF-06 review

**Kết quả:** HOLD.

Tài liệu review đã lập:

- `docs/governance/wf-06-document-search-review.md`

Kết luận chính:

- live/source WF-06 khớp, activeVersion không drift;
- node `🔐 Verify JWT` đứng trước query và có `onError=continueErrorOutput`;
- vẫn còn rủi ro dynamic SQL từ request body;
- Code node tự decode JWT nhưng không verify chữ ký và `userId` không tạo
  authorization boundary thật;
- DB/RLS boundary chưa được chứng minh vì thiếu Supabase read-only verification;
- cần negative tests hoặc remediation RPC/parameterized SQL trước PASS.

## 7. Điều kiện còn lại để đổi S1 từ HOLD sang GO CYCLE 2

| Điều kiện | Trạng thái |
|---|---|
| Required TypeScript Build & Lint SUCCESS trên current `main` | **PASS** |
| Required context luôn được tạo cho PR/push vào `main` | **SOURCE PASS; cần quan sát PR kế tiếp để chứng minh pull_request path** |
| Release/deploy sau CI fix | **PASS** |
| Supabase live verification read-only | **VERIFIED — FAIL/HOLD** |
| `run_fts_eval_v1` remediation source package | **READY_FOR_LIVE_APPROVAL** |
| Rollback/change-control 013–021d | **HOLD** |
| Governance Issue #2 / remote status | **OPEN / stale body; cần owner quyết định update/close** |
| WF-06 injection/authorization review | **HOLD** |

## 8. Quyết định

Không đủ điều kiện GO CYCLE 2.

**Quyết định sau remediation note:** **HOLD — Supabase đã verified nhưng phát hiện
function security drift, rollback `021d` unsafe, Issue #2 governance cần cập nhật
và WF-06 cần remediation hoặc negative test evidence.**

## 9. Remediation package lập sau S1

Đã tạo source package cho finding `run_fts_eval_v1`:

- `supabase/migrations/023_harden_run_fts_eval_v1.sql`
- `supabase/rollbacks/023_harden_run_fts_eval_v1_down.sql`
- `docs/checkpoints/s1-run-fts-eval-remediation.md`

Package này chưa apply live. Trạng thái: **READY_FOR_LIVE_APPROVAL**.
