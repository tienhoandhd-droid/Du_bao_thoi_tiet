# AGENTS.md — Hướng dẫn cho Codex GPT và Claude Code

> **Tài liệu canonical:** `nangcap.md` (kiến trúc + roadmap) + `kehoach.md` (kế hoạch 40 Chat)
> **Tham khảo lịch sử:** `CLAUDE.md` (Chat 01–20 đã hoàn thành — đọc nếu cần tra lịch sử, không cập nhật)
> **Điều phối thực hành:** `CRAVE-DIEU-PHOI-Codex-ClaudeCode.md` (prompt copy-paste từng Chat)
> **Repo:** `tienhoandhd-droid/Du_bao_thoi_tiet` · Supabase: `bdttccztjtrcaztjgkot`

Luôn trả lời bằng tiếng Việt.

---

## 1. Quy tắc an toàn — BẮT BUỘC mọi agent, mọi Chat

- Không `apply_migration` / không `execute_sql` ghi/sửa/xóa khi chưa trình bày SQL và nhận xác nhận.
- Không `update` / `execute` / `publish` / `unpublish` / `archive` workflow n8n khi chưa nhận xác nhận.
- Không push GitHub / tạo PR / đổi GitHub settings khi chưa báo cáo diff và nhận xác nhận.
- Không `INSERT` vào DB production khi chưa hỏi xác nhận.
- Chỉ sửa workflow prefix `TKTL` — không đụng `BMS-GMP`, `VMP`, `QMSTeam`, `GMP Kiểm Tạp`.
- Không dùng project Supabase `xrpnlpfcoarouoqkhgfp` — chỉ `bdttccztjtrcaztjgkot`.
- Không hard-code secret vào frontend, source code hoặc CONFIG node n8n.
- Mọi AI output GMP là DRAFT — AI không có quyền approve.
- Credentials n8n (whitelist): `GMP-check` + `OpenAl` + `CRAVE-Google-Workspace` (đã phê duyệt) + `CRAVE-Tavily` + `CRAVE-GitHub-Token` + `CRAVE-SMTP` (ba cái sau: tạo theo change-control khi cần). Credential ngoài danh sách → FAIL.
- JWT dùng Cách B: GET `/auth/v1/user` + header `apikey`, `onError=continueErrorOutput`.

---

## 2. Nguyên tắc không xung đột giữa hai agent

### 2.1 Mỗi Chat có một owner duy nhất
- Owner của Chat được khai báo trong `kehoach.md §5` (bảng phân công) và trong từng Chat card.
- Owner là người duy nhất được **tạo + sửa** file thuộc phạm vi Chat đó.
- Agent kia có thể **đọc** file đó để tham khảo, nhưng không được sửa.

### 2.2 File ownership
- Không hai agent sửa cùng file giữa hai System Check.
- Nếu cần chạm file thuộc phạm vi Chat khác → **dừng, ghi vào `[!] Chưa giải quyết`**, báo người dùng đổi thứ tự Chat.

### 2.3 HANDOFF PACKAGE
Kết thúc mỗi Chat, owner ghi đủ:
```
Files đã tạo/sửa: [đường dẫn + mô tả]
Nội dung paste cho agent tiếp theo: [file content hoặc "đã có trong repo"]
MCP operations agent tiếp theo cần làm: [list]
Unresolved: [nếu có]
Trạng thái: PASS / BLOCKED / READY_FOR_GITHUB_APPROVAL / READY_FOR_LIVE_APPROVAL
```

---

## 3. Khả năng thực tế

### Codex GPT
**Làm được:** viết SQL migration (idempotent + rollback), viết n8n WF JSON, viết TypeScript/React, viết scripts Python, viết prompts có versioning, đọc file qua paste.

**Không làm được:** đọc live Supabase/n8n, chạy Bash, apply migration, push GitHub, publish n8n.

**Skill mặc định:** `$crave-codex-builder` — áp dụng như checklist an toàn và chuẩn chất lượng, không áp lại mô hình builder/reviewer cũ.

### Claude Code
**Làm được:** đọc live Supabase/n8n qua MCP (read-only mặc định), chạy Bash/CLI, review code + schema với bằng chứng live, apply migration (sau xác nhận), push GitHub (sau xác nhận), publish n8n (sau xác nhận).

**Skill mặc định:** đọc `nangcap.md` + `kehoach.md` trước khi bắt đầu Chat. Không dùng mô hình builder/reviewer cũ.

---

## 4. Quy trình bắt đầu mỗi Chat

1. `git status` — kiểm tra không có uncommitted conflict từ Chat trước.
2. Đọc `kehoach.md §3` (quy tắc bắt buộc) và card Chat hiện tại.
3. Đọc file trực tiếp liên quan (phạm vi file của Chat này).
4. Kiểm tra live chỉ đọc nếu cần (Claude Code qua MCP; Codex qua paste).
5. Lập plan ngắn, sửa source theo phạm vi, tự kiểm.
6. Kết thúc bằng HANDOFF PACKAGE + trạng thái chuẩn.

---

## 5. Môi trường thực thi — nhóm không có local dev

Nếu không có máy local:
- **Docling / eval scripts:** chạy trong **GitHub Codespaces** (miễn phí 60h/tháng) hoặc máy team chuyên dụng.
- **Eval CI:** GitHub Actions workflow_dispatch — chạy theo yêu cầu, kết quả lưu vào `eval/reports/`.
- **SQL migration review:** Supabase Dashboard SQL Editor (đọc) — apply qua MCP sau xác nhận.

Tham khảo thêm: `nangcap.md §19`.

---

## 6. Tự kiểm tối thiểu mỗi Chat

- Syntax/format hợp lệ (SQL parse, TSC, JSON lint).
- Unit/static test + negative test phù hợp.
- Secret scan: không key/token/credential trong output.
- Diff check: chỉ file trong phạm vi đã thay đổi.
- Rollback: migration phải có rollback cùng số+tên tại `supabase/rollbacks/`.
- Rủi ro còn lại: ghi rõ để người dùng quyết định.
