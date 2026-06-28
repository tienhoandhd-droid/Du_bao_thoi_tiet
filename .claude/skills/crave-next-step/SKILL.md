---
name: crave-next-step
description: >
  Xác định bước tiếp theo trong kế hoạch 40-Chat CRAVE và in ra prompt copy-paste
  sẵn sàng dùng cho Codex GPT hoặc Claude Code. Đọc kehoach.md + git log để biết
  đang ở Chat nào, Chat tiếp theo là gì, và agent nào cần làm. Không thay đổi
  bất kỳ file nào — chỉ đọc và báo cáo. Dùng sau mỗi Chat PASS để biết làm gì tiếp.
---

# CRAVE NEXT STEP SKILL — "Bước tiếp theo là gì?"

> Khi gõ `/crave-next-step`, tôi sẽ đọc kế hoạch, xác định Chat tiếp theo và
> in ra **prompt copy-paste sẵn sàng dùng** — không cần tìm kiếm thủ công.

---

## THỰC HIỆN (tự động, không cần user chỉ định)

### 1. Đọc trạng thái hiện tại

```
a) git log --oneline -5          → Chat gần nhất đã commit là gì?
b) Đọc kehoach.md §5             → Bảng phân công Chat 01–40
c) Đọc kehoach.md §6–§13         → Tìm section Chat nào có dấu [x] Đã hoàn thành
d) git status                    → Có uncommitted work chưa?
```

### 2. Xác định Chat hiện tại và Chat tiếp theo

Logic:
- Chat đã PASS = có `[x] Đã hoàn thành` trong card VÀ/HOẶC commit liên quan trong git log
- Chat tiếp theo = Chat đầu tiên chưa có `[x] Đã hoàn thành`
- Nếu đang giữa chừng một Chat (có work uncommitted) → báo "Đang ở Chat XX, chưa PASS"

### 3. In ra kết quả theo format

```
══════════════════════════════════════════════════════
 CRAVE — BƯỚC TIẾP THEO
══════════════════════════════════════════════════════

 Đã hoàn thành: Chat 00 (Transition) + Chat 01 (Snapshot) + Chat 02 (Security)
 Chat tiếp theo: Chat 03 — Codex GPT — Reconcile Supabase source tới migration 022
 Owner: CODEX GPT
 Điều kiện tiên quyết: Chat 01 PASS ✅ + Chat 02 PASS ✅ → ĐỦ ĐIỀU KIỆN

══════════════════════════════════════════════════════
 PROMPT CHO CODEX GPT (copy toàn bộ block dưới đây)
══════════════════════════════════════════════════════

[in nguyên văn Prompt copy-paste từ card Chat 03 trong kehoach.md]

══════════════════════════════════════════════════════
 SAU KHI CODEX XÂY XONG
══════════════════════════════════════════════════════

 1. Nhận HANDOFF PACKAGE từ Codex
 2. Paste vào Claude Code (đây):
    "Chat 03 đã PASS từ Codex. HANDOFF PACKAGE: [paste]
     Xác nhận và tiếp tục Chat 04 nếu đủ điều kiện."

══════════════════════════════════════════════════════
 Chat SAU ĐÓ (preview): Chat 04 — Claude Code — Export 14 workflow TKTL
══════════════════════════════════════════════════════
```

---

## QUY TẮC THỰC HIỆN

- **Chỉ đọc** — không sửa file, không commit, không apply.
- Nếu không đọc được trạng thái rõ ràng (không có `[x]` trong kehoach.md) → dùng git log + git status để suy luận.
- Nếu có **HOLD** hoặc **BLOCKED** ở Chat trước → báo HOLD, không in prompt Chat tiếp theo.
- Nếu tiếp theo là **System Check** (S1–S8) → in prompt System Check tương ứng thay vì Chat công việc.
- In **tên owner rõ ràng**: "CODEX GPT" hoặc "CLAUDE CODE" bằng chữ hoa để dễ phân biệt.
- Luôn in **preview Chat sau đó** (Chat N+2) để user biết trước.

---

## VÍ DỤ ĐẦU RA ĐẦY ĐỦ

Giả sử Chat 01 và 02 đã PASS, Chat 03 chưa làm:

```
══════════════════════════════════════════════════════
 CRAVE — BƯỚC TIẾP THEO (2026-06-29)
══════════════════════════════════════════════════════

 ✅ Chat 00 — Transition Handoff (không cần thực thi)
 ✅ Chat 01 — Codex GPT — Snapshot, change register, file ownership (PASS)
 ✅ Chat 02 — Claude Code — GitHub secret/branch hardening (PASS)
 ⏳ Chat 03 — Codex GPT — Reconcile Supabase source tới migration 022
 ⏳ Chat 04 — Claude Code — Export và reconcile 14 workflow TKTL
 ⏳ Chat 05 — Codex GPT — Repo target structure, CI guardrails
 ⏳ S1      — Claude Code — System Check sau Chat 01–05

══════════════════════════════════════════════════════
 PROMPT CHO CODEX GPT — Chat 03 (copy từ dấu --- đến ---)
══════════════════════════════════════════════════════

---
[CODEX GPT — Chat 03 của CRAVE]
Canonical: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo lịch sử.
Supabase: bdttccztjtrcaztjgkot. Chỉ TKTL. Không BMS/VMP/QMS.
Bạn không có MCP — nhận nội dung live qua paste bên dưới.
Phạm vi file: supabase/baseline/, supabase/migrations/022_*.sql,
  supabase/rollbacks/022_*_down.sql, docs/architecture/supabase-source-map.md

Việc làm:
- Đọc nội dung live đã paste và migration repo hiện có
- Phục hồi migration 022_fix_eval_rank_order.sql nếu chưa có trong repo
- Tạo rollback 022_fix_eval_rank_order_down.sql
- Tạo supabase-source-map.md phân loại 001–022: exact/baseline-only/missing evidence
- Lập baseline cho table/function/policy quan trọng

Không execute SQL ghi. Không apply. Không bịa rollback thiếu bằng chứng.
Tự kiểm: SQL parse, idempotency, rollback honest, secret scan, diff check.
Kết thúc: HANDOFF PACKAGE + PASS/BLOCKED.

=== NỘI DUNG PASTE (lấy từ Claude Code trước khi paste cho Codex) ===
[Để lấy nội dung này, hỏi Claude Code:
 "Dùng MCP Supabase list_migrations và đọc definition migration 022, paste kết quả"]
---

══════════════════════════════════════════════════════
 SAU KHI CODEX XONG → paste cho Claude Code:
══════════════════════════════════════════════════════

"Chat 03 Codex đã PASS. HANDOFF PACKAGE: [paste HANDOFF từ Codex].
 Xem xét Chat 04 tiếp theo: Export 14 workflow TKTL."

══════════════════════════════════════════════════════
 Preview Chat 04 — CLAUDE CODE — Export 14 workflow TKTL
══════════════════════════════════════════════════════
```

---

## GHI CHÚ

- Skill này **không thay thế** `kehoach.md` — nó chỉ đọc và print nhanh.
- Nếu kehoach.md có cập nhật trạng thái `[x]` trong card Chat, skill sẽ tự nhận ra.
- Để cập nhật trạng thái Chat trong kehoach.md sau khi PASS, dùng:
  `/crave-claude-builder` (Chat của Claude Code) hoặc yêu cầu Codex cập nhật file.
