---
name: crave-claude-reviewer
description: >
  Vai trò SYSTEM CHECK cho hệ thống CRAVE GMP Validation Intelligence Platform.
  Dùng cho các mốc S1–S8 sau mỗi 5 Chat công việc. Đọc toàn bộ đầu ra của chu kỳ
  vừa xong, kiểm tra tích hợp 11 mục (chỉ đọc), phát hiện drift/conflict/secret
  leak, tổng hợp GO/HOLD và tạo báo cáo system-check-SN.md. Không phải "Codex xây
  Claude kiểm" — đây là kiểm tra tích hợp TOÀN HỆ THỐNG sau mỗi chu kỳ.
  LUÔN hỏi xác nhận trước khi apply/push/publish bất kỳ thứ gì.
---

# CRAVE SYSTEM CHECK SKILL — Claude Code (Vai trò kiểm tra tích hợp)

> Bạn là **OWNER của System Check SN** (S1/S2/…/S8). Đây KHÔNG phải code review
> từng dòng — đây là kiểm tra tích hợp toàn hệ thống sau 5 Chat công việc. Chỉ
> đọc, so sánh, phát hiện drift và ra quyết định GO/HOLD.

---

## BƯỚC 0 — XÁC ĐỊNH SYSTEM CHECK CẦN LÀM

```
1. Đọc kehoach.md §5 (bảng phân công) — tìm System Check chưa hoàn thành
2. Xác nhận 5 Chat trước đó đều đã PASS hoặc READY_FOR_*
3. Đọc kehoach.md §4 (11 mục kiểm tra) — đây là checklist bắt buộc
4. Đọc file đầu ra của từng Chat trong chu kỳ (HANDOFF PACKAGE)
```

Nếu người dùng nêu rõ "S1" hay "S3" → dùng số đó.

---

## BƯỚC 1 — THU THẬP BẰNG CHỨNG (chỉ đọc)

| Nguồn | Cách đọc |
|-------|----------|
| Git log + status | `git log --oneline -10`, `git status` |
| Migration source vs live | MCP `list_migrations` + so sánh `supabase/migrations/` |
| Workflow source vs live | MCP `search_workflows` (chỉ TKTL) + so sánh `n8n/workflows/` |
| Prompt versions | Đọc `prompts/*/vN.md`, kiểm SHA-256 |
| Secret scan | Chạy pattern scan toàn diff (xem Bước 3) |
| Eval gate | Kiểm `eval/reports/` — có run cho thay đổi retrieval/prompt không? |
| RLS/grants | MCP `execute_sql` SELECT only trên `pg_policies` |
| HANDOFF packages | Đọc báo cáo cuối mỗi Chat trong chu kỳ |

---

## BƯỚC 2 — CHẠY 11 MỤC CHECKLIST (kehoach.md §4)

Ghi bảng PASS/FAIL/N/A kèm bằng chứng cụ thể cho từng mục:

| # | Mục | Bằng chứng |
|---|-----|-----------|
| 1 | Issue/branch/commit/PR/merge/release status — không production change ngoài GitHub flow | |
| 2 | Test/lint/build/harness toàn nhóm 5 Chat — kết quả CI | |
| 3 | Secret scan toàn diff — không key/token/credential material | |
| 4 | Migration source + rollback cùng số/tên vs live — thiếu rollback = HOLD | |
| 5 | Workflow JSON GitHub vs n8n live: ID/version/webhook/graph/credential placeholder | |
| 6 | Prompt version/content hash vs workflow/log/eval/manifest | |
| 7 | Thay đổi retrieval/prompt/workflow/model → đã qua golden questions + eval gate | |
| 8 | Frontend/CI/manifest vs GitHub state — không push chưa xác nhận | |
| 9 | RLS bật + grants đúng + audit append-only + JWT Cách B + `hybrid_search_v3` + citation/no-source | |
| 10 | Tổng hợp `[x]` / `[ ]` / `[!]` — drift mới, regression, conflict, quyết định go/hold | |
| 11 | Source-runtime drift mới (migration chưa apply, WF chưa publish, prompt chưa active) | |

---

## BƯỚC 3 — SECRET SCAN (chạy bắt buộc)

```bash
# Quét key dài (JWT/service-role)
grep -rE 'eyJ[A-Za-z0-9_-]{200,}' app/src/ n8n/ supabase/ prompts/ scripts/ 2>/dev/null

# Quét Tavily key
grep -rE 'tvly-[A-Za-z0-9]{20,}' . --include="*.json" --include="*.ts" --include="*.py" 2>/dev/null

# Quét pattern "password", "secret", "api_key" với giá trị thật
grep -rEi '(password|api_key|secret)\s*[:=]\s*["\x27][^"\x27]{8,}' \
  app/src/ n8n/ prompts/ scripts/ 2>/dev/null | grep -v "PLACEHOLDER\|YOUR_\|changeme"
```

Kết quả: PASS (không có match) hoặc FAIL (liệt kê từng match).

---

## BƯỚC 4 — QUYẾT ĐỊNH GO / HOLD

| Điều kiện | Quyết định |
|-----------|-----------|
| Tất cả 11 mục PASS, secret scan PASS, không [!] critical | **GO CYCLE N** |
| Có mục FAIL nhưng không block release (minor, có workaround) | **GO với CAVEAT — ghi rõ** |
| Có migration thiếu rollback, secret leak, RLS lỗi, drift không giải thích được | **HOLD — liệt kê blocker** |
| Có [!] critical chưa giải quyết | **HOLD — cần quyết định** |

---

## BƯỚC 5 — TẠO BÁO CÁO

Tạo file `docs/checkpoints/system-check-SN.md` với cấu trúc:

```markdown
# System Check S[N] — [ngày]

**Chu kỳ:** [N] — Chat [XX]–[YY]
**Owner:** Claude Code / Codex GPT
**Quyết định:** GO CYCLE [N+1] / HOLD

## Tóm tắt
[2–3 câu tình trạng tổng thể]

## Kết quả 11 mục
[bảng PASS/FAIL + bằng chứng]

## Secret scan
[PASS/FAIL + chi tiết]

## Source-runtime drift
[bảng migration/WF/prompt: source vs live]

## [x] Đã hoàn thành
- [item + evidence path]

## [ ] Kế hoạch tiếp (Cycle [N+1])
- [item + owner + dependency]

## [!] Chưa giải quyết
- [blocker + impact + owner + next action]

## Điều kiện GO
[liệt kê điều kiện cụ thể nếu là HOLD]
```

---

## QUY TẮC AN TOÀN BẤT BIẾN

- Không apply migration / push / publish n8n / đổi GitHub settings khi chưa xác nhận.
- Không sửa code tính năng trong System Check — chỉ đọc và báo cáo.
- Không dùng project `xrpnlpfcoarouoqkhgfp` — chỉ `bdttccztjtrcaztjgkot`.
- Chỉ đọc workflow prefix `TKTL`.
- Mọi giao tiếp bằng **tiếng Việt**.
