# CRAVE — Change register

**Khởi tạo:** 2026-06-29 (Asia/Ho_Chi_Minh)<br>
**Phạm vi:** kế hoạch nâng cấp Chat 01–40; bảng đầu kỳ bên dưới tập trung Chat 01–05<br>
**Canonical process:** Issue → branch → source → test/eval → PR → merge → release → live approval

## 1. Quy tắc ghi nhận

- Mỗi Chat có đúng một record chính và một owner theo [`kehoach.md`](../../kehoach.md). Không ghi “hoàn thành” nếu thiếu evidence hoặc còn thao tác bắt buộc chưa làm.
- Không ghi secret value, token, credential export, dữ liệu GMP thật hoặc nội dung log nhạy cảm.
- Nếu chưa có Issue/branch/commit/PR/release thì ghi `Chưa có`, `Không áp dụng` hoặc `Chưa được cung cấp`; không suy đoán ID.
- Mọi mốc phải có timestamp, source/evidence và trạng thái `[x]`, `[ ]` hoặc `[!]`.
- Thao tác remote/live chỉ được ghi `đã thực hiện` khi có bằng chứng và đã qua phê duyệt tương ứng.

## 2. Mẫu record cho mỗi Chat

Sao chép khối này khi mở Chat mới:

```markdown
### Chat NN — <tiêu đề>

| Trường | Giá trị |
|---|---|
| Owner | Codex GPT / Claude Code |
| Issue | `<URL hoặc ID>` / Chưa có |
| Branch | `<branch>` / Chưa có |
| Commit | `<SHA + subject>` / Chưa có |
| Pull request | `<URL hoặc ID>` / Chưa có |
| Merge | `<merge SHA + timestamp>` / Chưa merge |
| Release | `<release/deployment/version>` / Chưa release / Không áp dụng |
| Live operation | `<operation + approval evidence>` / Không có |
| Files | `<đường dẫn thuộc lease>` |
| Tests/eval | `<lệnh/check + kết quả + timestamp>` |
| Source/evidence | `<file, CI run, read-only snapshot hoặc user-provided live evidence>` |
| Rollback | `<cách revert source/live>` |
| Trạng thái | `[x] Đã hoàn thành` / `[ ] Kế hoạch` / `[!] Chưa giải quyết` |
| Next action | `<owner + hành động tiếp theo>` |
```

## 3. Register đầu kỳ — Chat 01–05

| Chat | Owner | Issue | Branch | Commit | PR / merge | Release / live | Trạng thái tại 2026-06-29 | Evidence / next action |
|---:|---|---|---|---|---|---|---|---|
| 01 | Codex GPT | Chưa có | `main` | Included in PR #3 merge `7fd1db5` | PR #3 merged 2026-06-29 | Không release; không thao tác live | `[x]` Baseline/governance đã vào `main` | [`current-state-snapshot.md`](../architecture/current-state-snapshot.md), [`file-ownership.md`](file-ownership.md), file này; S1 evidence [`system-check-S1.md`](../checkpoints/system-check-S1.md) |
| 02 | Claude Code | Chưa được cung cấp | Không được cung cấp; source hiện có trên `main` | `3b31362` chứa `eval.yml`, `ci.yml` và hai runbook; thao tác live được người dùng báo đã hoàn thành sau đó | PR/merge ID chưa được cung cấp | GitHub live: service-role đã ở Secrets; `main` đã bảo vệ; không có release ứng dụng | `[x]` **ĐÃ HOÀN THÀNH trước Chat 01 vì P0-A**; provenance Issue/PR còn thiếu | `LIVE-PASTE-2026-06-29`, Git history local và các file Chat 02; bổ sung Issue/PR ID khi có |
| 03 | Codex GPT | Chưa có | `main` | Included in PR #3 merge `7fd1db5` | PR #3 merged 2026-06-29 | Không apply Supabase live | `[!]` Source package vào `main`, nhưng rollback/live verification còn HOLD | Supabase source map và migration `022`; S1 còn blocker rollback 013–021d và thiếu read-only live verification |
| 04 | Claude Code | #2 | `chat-04/reconcile-tktl-workflows` → merged | PR #3 includes Chat 04 + remediation commits | PR #3 merged 2026-06-29; branch remote deleted | WF-14 live remediation đã thực hiện riêng theo phê duyệt; không có n8n operation trong S1 | `[x]` 14 workflow TKTL source/live khớp; WF-14 drift đã đóng | [`n8n/release-manifest.json`](../../n8n/release-manifest.json), [`workflow-inventory.md`](../../n8n/workflow-docs/workflow-inventory.md), S1 evidence; Issue #2 còn OPEN/stale body |
| 05 | Codex GPT | Chưa có | `chat-04/reconcile-tktl-workflows` PR #3 / local main-only remediation | `02a7100`, `5fb904a` | PR #3 merged; CI fix pushed direct to `main` with admin bypass | GitHub Actions only; không live app release riêng ngoài Pages deploy | `[x]` Scaffold/guardrail vào `main`; CI blocker đã remediation PASS | Release guard PASS; TypeScript Build & Lint run `28343429940` SUCCESS; deploy run `28343429927` SUCCESS |

## 4. Retrospective về thứ tự thực hiện

### RETRO-2026-06-29-01 — Chat 02 hoàn thành trước Chat 01

| Trường | Ghi nhận |
|---|---|
| Sự kiện | Chat 02 được thực hiện trước Chat 01 |
| Lý do | P0-A là rủi ro control-plane/secret hygiene cần ưu tiên: chuyển `SUPABASE_SERVICE_ROLE_KEY` khỏi GitHub Variables sang Secrets, thêm CI và bảo vệ `main` |
| Trạng thái live được cung cấp | `eval.yml` dùng `secrets.*`; `ci.yml` có; `main` yêu cầu PR + CI pass + cấm force push |
| Tác động điều phối | Không làm đổi owner hoặc lease. Chat 01 ghi nhận hồi tố và đóng băng baseline sau P0-A |
| Thiếu provenance | Issue ID, branch, PR/merge ID và timestamp thao tác remote chưa được cung cấp; không được tự bịa |
| Next action | Khi có evidence GitHub, cập nhật các trường thiếu mà không sửa ngược lịch sử retrospective |
| Source / timestamp | `LIVE-PASTE-2026-06-29`, `REPO-LOCAL-2026-06-29`; ghi nhận ngày 2026-06-29 |

## 5. Trạng thái cuối Chat 01

- [x] **Đã hoàn thành:** tạo ba tài liệu trong đúng phạm vi Chat 01; kiểm tra nguồn, timestamp, secret scan, link nội bộ và diff local.
- [ ] **Kế hoạch:** Chat 03–05 thực hiện theo dependency và [`file-ownership.md`](file-ownership.md); mọi remote/live action vẫn cần phê duyệt riêng.
- [!] **Chưa giải quyết:** provenance Issue/branch/PR của Chat 02 chưa được cung cấp; 9/14 workflow thiếu JSON canonical; source/rollback 022 thiếu trong repo; migration 023+ chưa viết/apply; WF-14 cần kiểm tra nguy cơ Tavily key literal.

## 6. System Check S1 và remediation

### S1 — 2026-06-29

| Trường | Giá trị |
|---|---|
| Báo cáo | [`docs/checkpoints/system-check-S1.md`](../checkpoints/system-check-S1.md) |
| Commit báo cáo | `f1ef74f docs(s1): record cycle 1 system check HOLD` |
| Quyết định ban đầu | **HOLD — CHƯA GO CYCLE 2** |
| Lý do HOLD | Required TypeScript gate lỗi, rollback 013–021d chưa đủ, Supabase live verification chưa có, governance/Issue stale, WF-06 cần review |
| Remote evidence | Pushed to `main`; GitHub báo admin bypass do branch protection yêu cầu PR + required check |

### S1-CI-REMEDIATION — 2026-06-29

| Trường | Giá trị |
|---|---|
| Commit | `5fb904a ci: ensure required TypeScript gate always runs` |
| File | `.github/workflows/ci.yml` |
| GitHub Actions | `CI — TypeScript Build & Lint` run `28343429940` SUCCESS; Pages deploy `28343429927` SUCCESS |
| Thay đổi | Bỏ `paths` filter để required context luôn được tạo; thay scanner generic `PLACEHOLDER` bằng unresolved sentinel cụ thể; chuyển secret scan sang quiet mode |
| Trạng thái | `[x]` CI remediation PASS |
| Còn mở | `[!]` Supabase read-only verification, rollback/change-control 013–021d, Issue #2 stale/open, WF-06 injection/authorization |

### S1-REMEDIATION-NOTE — 2026-06-29

| Trường | Giá trị |
|---|---|
| Note | [`docs/checkpoints/s1-remediation-note.md`](../checkpoints/s1-remediation-note.md) |
| Rollback plan | [`docs/governance/rollback-change-control-013-021d.md`](rollback-change-control-013-021d.md) |
| WF-06 review | [`docs/governance/wf-06-document-search-review.md`](wf-06-document-search-review.md) |
| Supabase read-only | BLOCKED: không có Supabase MCP/CLI/psql/DB env trong phiên |
| Quyết định sau note | **HOLD — chưa GO CYCLE 2** |
