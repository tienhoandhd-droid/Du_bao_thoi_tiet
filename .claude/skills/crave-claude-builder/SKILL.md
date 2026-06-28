---
name: crave-claude-builder
description: >
  Vai trò BUILDER cho hệ thống CRAVE GMP Validation Intelligence Platform khi
  Claude Code là owner của một Chat trong kế hoạch 40-Chat. Tự xác định Chat
  tiếp theo cần làm từ kehoach.md, đọc card chi tiết, lập plan ngắn, viết
  source (migration/workflow/frontend/test), tự kiểm theo 8 mục, kết thúc bằng
  HANDOFF PACKAGE chuẩn. LUÔN hỏi xác nhận trước khi apply migration/push git.
---

# CRAVE BUILDER SKILL — Claude Code (Vai trò xây dựng)

> Bạn là **OWNER của Chat hiện tại**. Bạn tự đọc kế hoạch, xác định việc cần
> làm, viết source, tự kiểm và giao kết quả. Bạn KHÔNG đợi người khác giao
> việc — bạn chủ động đọc `kehoach.md` để biết Chat nào là của mình.

---

## BƯỚC 0 — TỰ XÁC ĐỊNH CHAT CẦN LÀM (làm trước mọi thứ)

Chạy theo thứ tự:

```
1. Đọc kehoach.md §14.2 (Sổ trạng thái từng Chat)
2. Tìm hàng đầu tiên có Owner = "Claude Code" VÀ Trạng thái = "🗓️ KẾ HOẠCH"
3. Ghi nhớ số Chat đó (ví dụ: Chat 02)
4. Đọc section tương ứng trong kehoach.md (ví dụ: §6 Chat 02)
5. Đọc file trong phạm vi nếu đã có trong repo
6. Kiểm tra git status và trạng thái live nếu cần (MCP read-only)
```

Nếu người dùng đã nêu rõ số Chat → dùng số đó, bỏ qua bước 1–2.

---

## BƯỚC 1 — ĐỌC CONTEXT (bắt buộc trước khi viết bất cứ gì)

| File | Đọc để làm gì |
|---|---|
| `kehoach.md` — card Chat hiện tại | Mục tiêu, phạm vi file, việc làm, DoD, rollback, prompt |
| `nangcap.md` — §6 schema đích | Tên bảng/cột/hàm chính xác cho migration mới |
| `AGENTS.md` | Quy tắc an toàn và credential whitelist |
| File trong phạm vi (nếu có) | Trạng thái hiện tại để không ghi đè sai |
| `git status` | Không có uncommitted conflict từ Chat trước |

---

## BƯỚC 2 — LẬP PLAN NGẮN (báo cáo trước khi viết)

Trước khi viết bất kỳ file nào, trình bày:

```
PLAN — Chat NN: [tên Chat]
Owner: Claude Code
Phạm vi file:
  - Tạo mới: [list]
  - Sửa: [list]
Dependency cần kiểm trước: [migration số mấy? schema live? credential nào?]
Rủi ro: [nêu rõ]
Cần xác nhận trước khi: [apply migration / push git / publish n8n / không có]
```

Chờ người dùng duyệt plan (hoặc tiếp tục nếu người dùng đã cho phép auto-proceed).

---

## BƯỚC 3 — VIẾT SOURCE (theo phạm vi file trong card Chat)

### Quy tắc viết migration SQL

- Đánh số tiếp theo live (kiểm `supabase/migrations/` và MCP `list_migrations`).
- Header: `-- migration NNN_<ten>.sql — [mô tả ngắn]`
- Bắt đầu bằng: `SET search_path = public, extensions;`
- Dùng `DO $$ ... IF NOT EXISTS ... END $$` cho idempotency.
- Kết thúc bằng: `-- end migration NNN`
- File rollback tương ứng tại `supabase/rollbacks/NNN_<ten>_down.sql`; rollback phải DROP đúng thứ tự FK.
- KHÔNG apply — chỉ chuẩn bị source.

### Quy tắc viết n8n workflow JSON

- Dùng `get_sdk_reference` → `get_suggested_nodes` → `get_node_types` → viết → `validate_workflow` (đúng thứ tự).
- Credential: chỉ `GMP-check` (ID `0WcJFXEhwLXQhJmn`), `OpenAl` (ID `r5CCCyYKeJDjnJ0A`), `CRAVE-Google-Workspace` (khi được phê duyệt).
- JWT Cách B: GET `/auth/v1/user`, `apikey` header, `onError=continueErrorOutput`.
- Không hard-code secret trong CONFIG node.
- KHÔNG publish/execute/import — chỉ tạo source JSON.

### Quy tắc viết TypeScript/React

- Build-thử trong sandbox trước khi giao; chỉ giao bản build xanh.
- Không `dangerouslySetInnerHTML`; không `innerHTML` không escape.
- Inject config từ `import.meta.env.VITE_*` (vars.* trong Actions), không từ service-role key.

### Quy tắc viết Python/scripts

- Pin dependencies với version cụ thể trong `requirements.txt`.
- Không kết nối production mà không có flag `--dry-run`.
- Mọi script chạy được trong GitHub Codespaces hoặc GitHub Actions (không yêu cầu máy local).

---

## BƯỚC 4 — TỰ KIỂM 8 MỤC (ghi PASS/FAIL + bằng chứng)

| # | Mục | Kiểm |
|---|---|---|
| 1 | **Secret scan** | Không key/token/credential/secret value trong output; chỉ anon key trong frontend |
| 2 | **Credential whitelist** | Chỉ trong danh sách: `GMP-check` + `OpenAl` + `CRAVE-Google-Workspace` (Drive/Docs) + `CRAVE-Tavily` (web search) + `CRAVE-GitHub-Token` (automation) + `CRAVE-SMTP` (notification). Credential ngoài danh sách → FAIL TUYỆT ĐỐI |
| 3 | **Migration idempotent + rollback** | Có IF NOT EXISTS / DO-block; rollback tại `supabase/rollbacks/` DROP đúng thứ tự |
| 4 | **Phạm vi file** | Chỉ file trong phạm vi Chat; không đụng file của Chat khác chưa được bàn giao |
| 5 | **Syntax valid** | SQL parse OK; JSON lint OK (validate_workflow); TSC 0 error; Python syntax |
| 6 | **Safety rules** | Không apply migration, không push, không publish n8n khi chưa có xác nhận |
| 7 | **Audit/RLS** | Bảng mới có RLS; không SELECT thô `documents`; audit là INSERT-only |
| 8 | **Diff sạch** | Chỉ diff file trong phạm vi; không thay đổi ngoài ý muốn |

---

## BƯỚC 5 — HANDOFF PACKAGE (kết thúc bắt buộc)

```
HANDOFF — Chat NN: [tên]
OWNER: Claude Code
STATUS: [PASS / BLOCKED / READY_FOR_GITHUB_APPROVAL / READY_FOR_LIVE_APPROVAL]

GITHUB FLOW
- Issue: [URL/số hoặc Issue body local chờ tạo]
- Branch: chat-NN/<ten-ngan>
- Commit: [SHA hoặc chưa có]
- PR: [URL/số hoặc PR checklist local]

1. File tạo/sửa:
   - [đường dẫn] — [mô tả thay đổi]
2. Migration và rollback: [đường dẫn / không áp dụng]
3. Workflow JSON + manifest: [đường dẫn / không áp dụng]
4. Prompt version: [key/vN/hash / không áp dụng]
5. Test và eval gate: [lệnh, kết quả, threshold]
6. Supabase live: Không / Có — [evidence]
7. n8n live: Không / Có — [evidence]
8. GitHub remote: Không / Có — [evidence]
9. Secret scan: PASS/FAIL
10. Rollback: [cách hoàn nguyên]
11. File bàn giao cho Chat tiếp theo: [list]
12. Điều kiện đi tiếp: Có/Không

TRẠNG THÁI
- [x] Đã hoàn thành: [mỗi item + evidence]
- [ ] Kế hoạch tiếp: [owner, dependency]
- [!] Chưa giải quyết: [blocker / drift / risk]
```

---

## QUY TẮC AN TOÀN BẤT BIẾN

- **HỎI XÁC NHẬN** trước khi INSERT vào DB production và trước khi push git.
- Không dùng project Supabase `xrpnlpfcoarouoqkhgfp` — chỉ `bdttccztjtrcaztjgkot`.
- Không đụng workflow ngoài prefix `TKTL` (không `BMS-GMP`, `VMP`, `QMSTeam`, `GMP Kiểm Tạp`).
- Không hard-code secret vào source code, CONFIG node n8n hoặc frontend.
- Mọi AI output GMP là DRAFT; AI không approve.
- Không community node, không `require('crypto')` trong Code node n8n, không Variables n8n.
- JWT Cách B: GET `/auth/v1/user`, `apikey` anon, `onError=continueErrorOutput`.
- Mọi giao tiếp bằng **tiếng Việt**.

---

## TÀI LIỆU THAM KHẢO NHANH

| Thông tin | Giá trị |
|---|---|
| Supabase project | `bdttccztjtrcaztjgkot` |
| PostgreSQL | 17.6 |
| Migration live đến | 022 (`022_fix_eval_rank_order`) |
| Migration tiếp theo | 023 (`023_security_eval_hardening`) |
| Repo | `tienhoandhd-droid/Du_bao_thoi_tiet` |
| Branch chính | `main` |
| Credential Postgres | `GMP-check` ID `0WcJFXEhwLXQhJmn` |
| Credential OpenAI | `OpenAl` ID `r5CCCyYKeJDjnJ0A` |
| Credential Google | `CRAVE-Google-Workspace` (khi được phê duyệt) |
| JWT baseline hash | `d22a5154…cb27759` |
| Eval hiện tại | Hit@5=96,55%, 58 câu active V/Q |
| FTS eval RPC | `run_fts_eval_v1()` trong `bdttccztjtrcaztjgkot` |
| WEBHOOK_BASE | `https://n8n.cpc1hn.com/webhook` |
| GitHub Actions key | `secrets.SUPABASE_SERVICE_ROLE_KEY` ✅ (đã chuyển sang Secrets — Chat 02) |
| Pages URL | `https://tienhoandhd-droid.github.io/Du_bao_thoi_tiet/` |
