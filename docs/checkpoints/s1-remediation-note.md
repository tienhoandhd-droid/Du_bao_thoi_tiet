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

**Kết quả:** BLOCKED / NOT VERIFIED.

Phiên hiện tại không có công cụ phù hợp để đọc live Supabase:

- không có Supabase MCP trong MCP resources;
- không có `supabase` CLI;
- không có `psql`;
- không có biến môi trường kết nối DB;
- không chạy SQL qua service role hoặc dashboard.

Do đó các mục sau chưa được xác minh live trong remediation này:

- live migration list/head;
- RLS enabled/forced state;
- policies/grants;
- function owner/signature/security definer/search path;
- audit append-only controls;
- dữ liệu/rủi ro rollback `021d`.

Query pack cần chạy đã được ghi tại
`docs/governance/rollback-change-control-013-021d.md`.

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
| Supabase live verification read-only | **BLOCKED / NOT VERIFIED** |
| Rollback/change-control 013–021d | **HOLD** |
| Governance Issue #2 / remote status | **OPEN / stale body; cần owner quyết định update/close** |
| WF-06 injection/authorization review | **HOLD** |

## 8. Quyết định

Không đủ điều kiện GO CYCLE 2.

**Quyết định sau remediation note:** **HOLD — cần Supabase read-only access,
rollback change-control approval, Issue #2 governance update và WF-06 remediation
hoặc negative test evidence.**
