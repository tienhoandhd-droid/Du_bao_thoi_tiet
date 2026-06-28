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
| 01 | Codex GPT | Chưa có | Local `main`; không tạo branch remote | Chưa commit | Chưa có PR / chưa merge | Không release; không thao tác live | `[x]` Ba tài liệu baseline đã tạo local; chờ review/commit theo GitHub-first | [`current-state-snapshot.md`](../architecture/current-state-snapshot.md), [`file-ownership.md`](file-ownership.md), file này; owner tiếp theo review diff |
| 02 | Claude Code | Chưa được cung cấp | Không được cung cấp; source hiện có trên `main` | `3b31362` chứa `eval.yml`, `ci.yml` và hai runbook; thao tác live được người dùng báo đã hoàn thành sau đó | PR/merge ID chưa được cung cấp | GitHub live: service-role đã ở Secrets; `main` đã bảo vệ; không có release ứng dụng | `[x]` **ĐÃ HOÀN THÀNH trước Chat 01 vì P0-A**; provenance Issue/PR còn thiếu | `LIVE-PASTE-2026-06-29`, Git history local và các file Chat 02; bổ sung Issue/PR ID khi có |
| 03 | Codex GPT | Chưa có | Chưa có | Chưa có | Chưa có | Chưa release; không apply live | `[ ]` Kế hoạch | Reconcile Supabase baseline/source 022 theo lease; cần definition live do Claude xác minh, không đoán |
| 04 | Claude Code | Chưa có | Chưa có | Chưa có | Chưa có | Chưa release; không update/publish n8n | `[ ]` Kế hoạch | Export/redact 14 workflow TKTL, workflow docs và release manifest; xử lý drift 9/14 |
| 05 | Codex GPT | Chưa có | Chưa có | Chưa có | Chưa có | Chưa release | `[ ]` Kế hoạch | Tạo scaffold docs/prompts/eval/scripts và GitHub templates theo lease |

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
