# CRAVE — Hướng dẫn điều phối 2 nhân lực (Codex GPT ↔ Claude Code)
> **Tài liệu canonical:** `nangcap.md` (kiến trúc) + `kehoach.md` (kế hoạch 40 Chat)
> **Tham khảo lịch sử:** `CLAUDE.md` (Chat 01–20 đã hoàn thành — chỉ đọc, không cập nhật)
> **Cập nhật:** 2026-06-28 — bắt đầu từ Chat 01 kế hoạch mới (điểm xuất phát: migration 022, eval 96.55%, 14 WF active)

---

## 0. QUY TẮC VÀNG — ĐỌC 1 LẦN, NHỚ MÃI

```
┌─────────────────────────────────────────────────────────────────┐
│  MỖI CHAT = MỘT OWNER — KHÔNG HAI NGƯỜI SỬA CÙNG FILE          │
│                                                                 │
│  Codex GPT: XÂY (SQL migration, WF JSON, TS code, scripts)     │
│  Claude Code: KIỂM (đọc live Supabase/n8n, review, apply)      │
│                                                                 │
│  Luồng bắt buộc:                                                │
│  Issue → Branch → Source → Test/Eval → PR → Merge → Live       │
│                                                                 │
│  KHÔNG apply migration / KHÔNG push / KHÔNG publish n8n         │
│  khi chưa trình bày diff và nhận xác nhận của người dùng.       │
└─────────────────────────────────────────────────────────────────┘
```

**Nguyên tắc không xung đột:**
1. Mỗi Chat có danh sách **phạm vi file** riêng — không đụng file của Chat khác.
2. Codex GPT **không đọc được live** — nhận nội dung qua paste. Claude Code đọc live qua MCP (read-only trừ khi có xác nhận).
3. Kết thúc mỗi Chat bằng **HANDOFF PACKAGE** hoặc một trong bốn trạng thái chuẩn.

---

## 1. KHẢ NĂNG THỰC TẾ CỦA TỪNG AGENT

| Khả năng | Codex GPT | Claude Code |
|----------|-----------|-------------|
| Đọc file GitHub | ✅ (paste vào) | ✅ (Read tool) |
| Đọc live Supabase | ❌ | ✅ MCP (read-only mặc định) |
| Đọc live n8n | ❌ | ✅ MCP (read-only mặc định) |
| Chạy Bash / CLI | ❌ | ✅ (trong sandbox) |
| Viết SQL migration | ✅ (xuất file) | ✅ (review + sửa) |
| Viết n8n WF JSON | ✅ (xuất file) | ✅ (review) |
| Viết TypeScript | ✅ | ✅ |
| Apply migration | ❌ | ✅ (sau xác nhận) |
| Push GitHub | ❌ | ✅ (sau xác nhận) |
| Publish n8n WF | ❌ | ✅ (sau xác nhận) |

**Phân công nguyên tắc:**
- **Codex GPT** nhận Chat có đầu ra chủ yếu là **tạo mới file** (migration SQL, WF JSON, scripts, prompts, scaffold).
- **Claude Code** nhận Chat có đầu ra chủ yếu là **kiểm tra live + sửa + apply** (reconcile, review, security, export).
- **Mỗi 5 Chat** có 1 **System Check** do người còn lại thực hiện (chỉ đọc, không code tính năng).

---

## 2. BẢNG PHÂN CÔNG 8 CHU KỲ

| Chu kỳ | Chat | Chủ đề | Owner Codex | Owner Claude | Checkpoint |
|--------|------|---------|------------|--------------|------------|
| 1 | 01–05 | Baseline, GitHub, Supabase/n8n source | 01, 03, 05 | 02, 04 | S1 — Claude Code |
| 2 | 06–10 | Security, Docling, document versioning | 06, 09, 10 | 07, 08 | S2 — Codex GPT |
| 3 | 11–15 | Embedding, observability, schema | 11, 14 | 12, 13, 15 | S3 — Claude Code |
| 4 | 16–20 | Hybrid RAG, citation, RLS, audit | 16, 18, 20 | 17, 19 | S4 — Codex GPT |
| 5 | 21–25 | Eval 4 lane, DRAFT controlled | 22, 24 | 21, 23, 25 | S5 — Claude Code |
| 6 | 26–30 | Google Docs, frontend, backup | 27, 29 | 26, 28, 30 | S6 — Codex GPT |
| 7 | 31–35 | Glossary UI, reviewer, agent, dashboard | 31, 33, 35 | 32, 34 | S7 — Claude Code |
| 8 | 36–40 | Knowledge graph, cache, scaling, LLM | 37, 39 | 36, 38, 40 | S8 — Codex GPT |

> Xem chi tiết từng Chat (DoD, phạm vi file, rollback) trong `kehoach.md §6–§13`.

---

## 3. HANDOFF PACKAGE — FORMAT CHUẨN

Mỗi Chat kết thúc phải ghi đủ phần này (dán vào cuối báo cáo Chat):

```
=== HANDOFF PACKAGE — Chat XX (Owner: Codex GPT / Claude Code) ===

Files đã tạo/sửa:
  - path/to/file1.sql  (mô tả ngắn)
  - path/to/file2.tsx  (mô tả ngắn)

Nội dung cần paste cho agent tiếp theo (nếu Codex → Claude):
  [tên file] — [dán toàn bộ nội dung hoặc ghi "đã có trong repo"]

MCP operations agent tiếp theo cần thực hiện (nếu Claude):
  - Supabase: đọc schema bảng X, so sánh với migration Y
  - n8n: đọc workflow WF-ZZ, kiểm version

Unresolved (cần quyết định trước khi tiếp):
  - [nếu có]

Trạng thái: PASS / BLOCKED / READY_FOR_GITHUB_APPROVAL / READY_FOR_LIVE_APPROVAL
```

---

## 4. CÂU LỆNH ĐIỀU PHỐI (không cần nhớ bước kế tiếp)

Sau khi một Chat PASS, **dán câu này vào Claude Code**:

```
Chat vừa rồi đã PASS. Hãy:
1) Đọc kehoach.md và cho tôi biết Chat TIẾP THEO là gì, owner là ai (Codex hay Claude Code), và điều kiện tiên quyết đã đủ chưa.
2) IN RA nguyên văn Prompt copy-paste của Chat tiếp theo từ kehoach.md (ô tương ứng với owner).
3) Nếu owner là Codex GPT: liệt kê nội dung file nào tôi cần paste vào phiên Codex (vì Codex không đọc live được).
4) Nếu owner là Claude Code: liệt kê MCP operations cần làm và xác nhận nào cần hỏi người dùng trước.
Mọi giải thích bằng tiếng Việt.
```

> **Nếu quên đang ở Chat nào:** dán vào Claude Code: *"Đọc kehoach.md và nangcap.md, cho tôi biết Chat hiện tại là gì, đã PASS tới đâu và câu lệnh kế tiếp."*

---

## 5. HEADER BẮT ĐẦU PHIÊN — DÁN ĐẦU MỖI CHAT

### Cho Codex GPT (dán trước prompt Chat XX):
```
[CODEX GPT — Chat XX của CRAVE]
Canonical documents: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo lịch sử.
Supabase: bdttccztjtrcaztjgkot. Chỉ workflow prefix TKTL. Không đụng BMS/VMP/QMS.
Bạn KHÔNG có MCP tools — nhận file content qua paste bên dưới.
Phạm vi file Chat này: [điền từ kehoach.md]
Không apply SQL / không publish n8n / không push GitHub khi chưa có xác nhận.
Kết thúc bằng HANDOFF PACKAGE và PASS/BLOCKED.

Nội dung file cần thiết:
[paste nội dung các file liên quan]
```

### Cho Claude Code (dán trước prompt Chat XX):
```
[CLAUDE CODE — Chat XX của CRAVE]
Canonical documents: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo lịch sử.
Supabase: bdttccztjtrcaztjgkot (MCP read-only trừ khi được xác nhận).
Chỉ workflow prefix TKTL. Không đụng BMS/VMP/QMS.
Phạm vi file Chat này: [điền từ kehoach.md]
HANDOFF từ Chat trước: [paste HANDOFF PACKAGE]
Không apply/push/publish khi chưa hỏi xác nhận người dùng.
Kết thúc bằng HANDOFF PACKAGE và PASS/BLOCKED/READY_FOR_*.
```

---

## 6. PROMPT COPY-PASTE — CHU KỲ 1 (Chat 01–05 + S1)

> Chat 01–05 lấy từ `kehoach.md §6`. Dưới đây là bản tóm gọn sẵn để dán nhanh.

---

### Chat 01 — Codex GPT — Snapshot, change register, file ownership

**Phạm vi file:** `docs/governance/change-register.md`, `docs/governance/file-ownership.md`, `docs/architecture/current-state-snapshot.md`

```
[CODEX GPT — Chat 01 của CRAVE]
Canonical documents: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo lịch sử.
Supabase: bdttccztjtrcaztjgkot. Chỉ TKTL workflows. Không BMS/VMP/QMS.
Bạn không có MCP tools. Nhận thông tin qua nội dung paste bên dưới.
Phạm vi file: docs/governance/change-register.md, docs/governance/file-ownership.md, docs/architecture/current-state-snapshot.md

Việc làm: Đọc AGENTS.md và nangcap.md (đã paste). Tạo 3 tài liệu:
1) current-state-snapshot: 33 bảng / 14 WF / migration 001–022 / credential inventory / known drift
2) change-register: template ghi Issue/branch/commit/PR/release cho mọi Chat
3) file-ownership: bảng file lease Chat 01–05 (ai sở hữu file nào, lock period)

Không ghi secret value. Mọi con số phải có timestamp/source. Tự kiểm secret scan.
Kết thúc: HANDOFF PACKAGE + PASS/BLOCKED.

=== NỘI DUNG FILE ĐỂ THAM KHẢO ===
[Paste nội dung nangcap.md §3 (kiểm tra trạng thái) + AGENTS.md]
```

---

### Chat 02 — Claude Code — GitHub secret/branch hardening source package

**Phạm vi file:** `.github/workflows/eval.yml`, `.github/workflows/ci.yml`, `docs/sop/github-secret-rotation.md`, `docs/governance/github-branch-policy.md`

```
[CLAUDE CODE — Chat 02 của CRAVE]
Canonical: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo.
Supabase: bdttccztjtrcaztjgkot (MCP read-only). Chỉ TKTL.
Phạm vi file: .github/workflows/eval.yml, .github/workflows/ci.yml, docs/sop/github-secret-rotation.md, docs/governance/github-branch-policy.md
HANDOFF từ Chat 01: [paste HANDOFF PACKAGE Chat 01]

Việc làm:
- Sửa eval.yml và ci.yml: dùng secrets.SUPABASE_SERVICE_ROLE_KEY (không vars.*), least permissions, safe triggers, concurrency control
- Tạo github-secret-rotation.md: quy trình rotate key với dry-run/rollback
- Tạo github-branch-policy.md: đề xuất bảo vệ main (required checks, no force push)
- Không đổi GitHub settings thật; không rotate key thật; không push

Tự kiểm: workflow YAML syntax, fork/untrusted event analysis, log không echo secret, permissions tối thiểu.
Báo cáo: diff local + danh sách thao tác remote cần người dùng xác nhận.
Kết thúc: HANDOFF PACKAGE + PASS/BLOCKED/READY_FOR_GITHUB_APPROVAL.
```

---

### Chat 03 — Codex GPT — Reconcile Supabase source tới migration 022

**Phạm vi file:** `supabase/baseline/`, `supabase/migrations/022_fix_eval_rank_order.sql`, `supabase/rollbacks/022_fix_eval_rank_order_down.sql`, `docs/architecture/supabase-source-map.md`

```
[CODEX GPT — Chat 03 của CRAVE]
Canonical: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo.
Supabase: bdttccztjtrcaztjgkot. Chỉ TKTL. Không BMS/VMP/QMS.
Bạn không có MCP — nhận nội dung live qua paste bên dưới.
Phạm vi file: supabase/baseline/, supabase/migrations/022_*.sql, supabase/rollbacks/022_*_down.sql, docs/architecture/supabase-source-map.md

Việc làm:
- Đọc nội dung live (đã paste) và migration repo hiện có
- Phục hồi migration 022_fix_eval_rank_order.sql nếu chưa có trong repo (exact semantics, đã redaction)
- Tạo rollback 022_fix_eval_rank_order_down.sql
- Tạo supabase-source-map.md phân loại 001–022: exact / baseline-only / missing evidence
- Lập baseline cho các table/function/policy quan trọng

Không execute SQL ghi. Không apply migration. Không bịa rollback nếu không đủ bằng chứng.
Tự kiểm: SQL parse, idempotency, rollback honest, secret scan, diff check.
Kết thúc: HANDOFF PACKAGE + PASS/BLOCKED.

=== NỘI DUNG PASTE ===
[Paste output từ Claude Code: danh sách migration live + definition của migration 022]
```

---

### Chat 04 — Claude Code — Export và reconcile 14 workflow TKTL

**Phạm vi file:** `n8n/workflows/`, `n8n/workflow-docs/`, `n8n/release-manifest.json`

```
[CLAUDE CODE — Chat 04 của CRAVE]
Canonical: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo.
Supabase: bdttccztjtrcaztjgkot. MCP n8n read-only. Chỉ TKTL.
Phạm vi file: n8n/workflows/, n8n/workflow-docs/, n8n/release-manifest.json
HANDOFF từ Chat 03: [paste HANDOFF PACKAGE Chat 03]

Việc làm:
- Dùng MCP n8n đọc read-only 14 workflow TKTL (WF-01…WF-14)
- Export mỗi WF: ID, name, version, activeVersion, webhook path, node graph, credential NAME (không material)
- Phát hiện và ghi rõ WF-14 Tavily key literal nếu còn trong CONFIG node
- Tạo release-manifest.json và workflow-docs/
- Không update/execute/publish/import n8n; không credential material trong output

Tự kiểm: parse JSON, compare live graph, JWT Cách B, credential placeholder, secret scan, đặc biệt WF-14.
DoD: 14 JSON canon hoặc ghi rõ WF nào chưa thể canon.
Kết thúc: HANDOFF PACKAGE + PASS/BLOCKED.
```

---

### Chat 05 — Codex GPT — Repo target structure, CI guardrails

**Phạm vi file:** `docs/`, `prompts/`, `eval/`, `scripts/` (scaffold), `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`

```
[CODEX GPT — Chat 05 của CRAVE]
Canonical: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo.
Supabase: bdttccztjtrcaztjgkot. Chỉ TKTL. Không BMS/VMP/QMS.
Bạn không có MCP. Nhận thông tin qua paste bên dưới.
Phạm vi file: docs/ (scaffold), prompts/ (scaffold), eval/ (scaffold), scripts/ (scaffold), .github/ISSUE_TEMPLATE/, .github/pull_request_template.md
HANDOFF từ Chat 04: [paste HANDOFF PACKAGE Chat 04]

Việc làm:
- Tạo cây thư mục đích theo nangcap.md §8 (không move app/)
- Tạo ISSUE_TEMPLATE và PR template với checklist đúng
- Tạo script validate release manifest: guard migration thiếu rollback, WF thiếu export, prompt thiếu version, secret pattern
- README/placeholder cho mỗi thư mục mới

Không move app/. Không sửa live. Không push.
Tự kiểm: CI chạy validator trên dữ liệu giả; positive + negative test; không commit report GMP thật.
Kết thúc: HANDOFF PACKAGE + PASS/BLOCKED.

=== NỘI DUNG PASTE ===
[Paste nangcap.md §8 (cây repo đích)]
```

---

### System Check S1 — Claude Code — Sau Chat 01–05

```
[CLAUDE CODE — System Check S1 của CRAVE]
Canonical: nangcap.md + kehoach.md. CLAUDE.md chỉ tham khảo.
Supabase: bdttccztjtrcaztjgkot. MCP read-only. Không thay đổi production.
Đây là System Check — KHÔNG phải code tính năng và KHÔNG phải review theo mô hình cũ.

Kiểm tích hợp read-only 11 mục (xem kehoach.md §4):
1. Issue/branch/commit/PR/merge status và file ownership
2. Test/lint/build/harness toàn nhóm 5 Chat
3. Secret scan toàn diff
4. Migration source/rollback cùng số+tên vs live
5. Workflow JSON GitHub vs n8n live (ID/version/webhook/graph/credential)
6. Prompt version/hash vs workflow/log/eval/manifest
7. Golden questions + eval gate: thay đổi retrieval/prompt/model đã chạy chưa?
8. Frontend/CI/manifest vs GitHub state
9. RLS/grants/append-only/JWT Cách B/hybrid_search_v3/citation/no-source
10. Tổng hợp [x] Đã hoàn thành / [ ] Kế hoạch / [!] Chưa giải quyết
11. Drift mới, regression, file conflict, quyết định go/hold

Đầu ra: tạo docs/checkpoints/system-check-S1.md với quyết định GO CYCLE 2 hoặc HOLD.
Không apply, không update/publish, không đổi settings, không push.
```

---

## 7. CHECKLIST MỖI NGÀY LÀM VIỆC

```
Trước khi mở phiên:
1. Mở Claude Code (trong thư mục ~/Desktop/Du_bao_thoi_tiet)
2. Hỏi: "Đọc kehoach.md, tôi đang ở Chat nào, câu lệnh kế tiếp là gì?"
3. Làm đúng 1 Chat/phiên — không nhảy cóc
4. Dùng Header bắt đầu phiên (Mục 5) phù hợp với owner
5. Chat PASS → dán Câu lệnh Điều phối (Mục 4) → nhận prompt Chat kế
6. Lưu HANDOFF PACKAGE vào file local trước khi đóng phiên
```

---

## 8. SƠ ĐỒ LUỒNG TỔNG

```
       BẮT ĐẦU CHAT
            │
            ▼
    ┌──────────────────┐
    │ Dán Header phiên │  (Mục 5 — Codex hoặc Claude)
    └────────┬─────────┘
             │
    ┌────────▼──────────────────────────────┐
    │ Agent XÂY / KIỂM theo phạm vi file    │
    │ (không đụng file ngoài phạm vi)        │
    └────────┬──────────────────────────────┘
             │
    ┌────────▼─────────┐
    │  Tự kiểm + Báo   │
    │  cáo diff + rủi  │
    └────────┬─────────┘
             │
       ┌─────┴─────┐
       ▼           ▼
     FAIL        PASS
       │           │
       │    ┌──────▼──────┐
       │    │ HANDOFF PKG │
       │    └──────┬──────┘
       │           │
       │    ┌──────▼──────────┐
       │    │ Dán Câu lệnh    │
       │    │ Điều phối       │
       │    │ → Claude Code   │
       │    └──────┬──────────┘
       │           │
       │    Claude Code in ra
       │    Prompt Chat tiếp theo
       │           │
       │           ▼
       └──► CHAT TIẾP THEO
            (gửi lỗi cho agent
             owner để sửa)
```

---

> **Nguyên tắc bất biến:** Codex xây file, Claude Code xác nhận và apply. Không Chat nào đụng file của Chat khác giữa hai System Check. Khi nghi ngờ → dừng và hỏi người dùng.
