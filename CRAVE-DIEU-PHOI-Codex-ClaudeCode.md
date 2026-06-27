# CRAVE — Hướng dẫn điều phối 2 nhân lực (Codex ↔ Claude Code)

> **Cách dùng tài liệu này:** Đây là "bảng điều khiển" cho toàn bộ quá trình nâng cấp. Mỗi hạng mục có 2 ô câu lệnh: **ô CODEX** (dán vào ChatGPT/Codex) và **ô CLAUDE CODE** (dán vào terminal Claude Code). Làm tuần tự từ Hạng mục 1. Không nhảy cóc.

---

## 0. QUY TẮC VÀNG (đọc 1 lần, nhớ mãi)

**Mỗi hạng mục = 2 pha, dán cho 2 bên theo đúng thứ tự:**

```
┌─────────────────────────────────────────────────────────────┐
│  HẠNG MỤC N                                                  │
│                                                             │
│  PHA 1 ──► Dán ô CODEX vào ChatGPT/Codex                    │
│           Codex XÂY (migration + workflow + frontend)       │
│           Codex báo: "SẴN SÀNG BÀN GIAO CLAUDE CODE"        │
│                                                             │
│  PHA 2 ──► Dán ô CLAUDE CODE vào terminal Claude Code      │
│           Claude Code KIỂM TRA 11 mục + SỬA nếu lỗi        │
│           Claude Code báo: "PASS — SẴN SÀNG PRODUCTION"     │
│                                                             │
│  PHA 3 ──► Dán "CÂU LỆNH ĐIỀU PHỐI" vào Claude Code        │
│           → tự cập nhật HandOFF + in câu lệnh hạng mục kế  │
└─────────────────────────────────────────────────────────────┘
```

**Chỉ chuyển sang hạng mục tiếp theo KHI Claude Code đã báo PASS.** Nếu Claude Code báo FAIL → quay lại dán cho Codex sửa (kèm danh sách lỗi Claude Code đưa ra), rồi lặp lại Pha 2.

**Trước khi bắt đầu bất kỳ hạng mục nào**, đảm bảo 2 skill đã được cài:
- Skill `crave-codex-builder` → đặt trong project Codex (hoặc dán đầu mỗi phiên Codex)
- Skill `crave-claude-reviewer` → đã lưu tại `.claude/skills/crave-claude-reviewer/SKILL.md` trong repo

> Nội dung 2 skill này nằm ở Phần E của whitepaper. Nếu chưa cài, làm việc đó trước (xem Mục 6 bên dưới).

---

## 1. THỨ TỰ LÀM (lộ trình 4 giai đoạn)

Làm từ trên xuống. Mỗi hạng mục xong (PASS) mới qua hạng mục kế.

| # | Hạng mục | Giai đoạn | Điều kiện được phép bắt đầu |
|---|----------|-----------|------------------------------|
| 1 | **Chat 10 — Citation Grounding** | GĐ1: Nền tảng đo lường | Bắt đầu ngay |
| 2 | **Chat 11 — Eval Harness + Golden 50–100 câu** | GĐ1: Nền tảng đo lường | Sau khi #1 PASS |
| 3 | **Chat 12 — Adaptive/CRAG Routing** | GĐ2: Agent | Sau khi #2 PASS (faithfulness ≥0.90) |
| 4 | **Chat 13 — AI Agent WF-12 + Memory** | GĐ2: Agent | Sau khi #2 PASS (BẮT BUỘC có eval trước) |
| 5 | **Chat 14 — Observability** | GĐ2: Agent | Sau khi #4 PASS |
| 6 | **Chat 16 — Validation Copilot** | GĐ3: Nghiệp vụ | Sau khi #4, #5 PASS |
| 7 | **Chat 17 — AI Reviewer** | GĐ3: Nghiệp vụ | Sau khi #6 PASS |
| 8 | **Chat 18 — Deviation Investigator** | GĐ3: Nghiệp vụ | Sau khi #7 PASS |
| 9 | **Chat 15 — Equipment Knowledge Graph** | GĐ4: Tối ưu | Sau khi GĐ3 xong |
| 10 | **Chat 19 — Prompt Registry + Governance** | GĐ4: Tối ưu | Sau khi #9 PASS |
| 11 | **Chat 20 — Semantic Cache có version** | GĐ4: Tối ưu | Sau khi #10 PASS |

> **Vì sao thứ tự này?** Citation grounding (#1) + Eval (#2) phải làm TRƯỚC mọi thứ, vì nếu không có thước đo thì mỗi lần sửa Agent/prompt sau này đều "mù" — không biết hệ thống tốt lên hay xấu đi. Agent (#4) chỉ build sau khi có Eval để đo hồi quy. Copilot/Reviewer (#6–8) là tính năng nghiệp vụ cao cấp, dựa trên Agent. Tối ưu (#9–11) làm cuối.

---

## 2. CÂU LỆNH ĐIỀU PHỐI (bí quyết để luôn biết bước kế tiếp)

**Đây là câu trả lời cho câu hỏi "làm sao biết câu lệnh dán tiếp theo".** Sau khi Claude Code báo PASS một hạng mục, anh **dán câu này vào Claude Code** (chỉ Claude Code, không phải Codex):

```
Hạng mục vừa rồi đã PASS. Hãy:
1) Cập nhật file 00-HANDOFF-CRAVE.md (hoặc CLAUDE.md): đánh dấu hạng mục này ✅ HOÀN THÀNH trong mục Lộ trình và Nhật ký, ghi ngày hôm nay, tóm tắt thay đổi đã làm (migration số mấy, workflow nào, frontend gì), rồi commit với message rõ ràng.
2) Cho tôi biết hạng mục TIẾP THEO trong lộ trình là gì (theo bảng thứ tự), và điều kiện tiên quyết đã đủ chưa.
3) IN RA cho tôi nguyên văn 2 câu lệnh của hạng mục tiếp theo: ô CODEX (để tôi dán vào ChatGPT) và ô CLAUDE CODE (để tôi dán lại cho bạn sau khi Codex xây xong). Điền sẵn đúng tên hạng mục, số migration tiếp theo, và tên workflow TKTL phù hợp.
Mọi giải thích bằng tiếng Việt.
```

Claude Code sẽ tự đọc HandOFF, biết đang ở đâu, và **in ra sẵn 2 ô câu lệnh cho hạng mục kế tiếp** — anh chỉ việc copy. Không phải tự nhớ, không phải tra tài liệu này mỗi lần.

> **Mẹo:** Nếu lỡ quên đang ở hạng mục nào, chỉ cần mở Claude Code và dán: *"Đọc 00-HANDOFF-CRAVE.md và cho tôi biết tôi đang ở hạng mục nào, đã PASS tới đâu, và câu lệnh kế tiếp là gì."*

---

## 3. CÁC Ô CÂU LỆNH THEO TỪNG HẠNG MỤC

> Dưới đây là câu lệnh cho **3 hạng mục đầu** (đã thiết kế chi tiết). Từ hạng mục #4 trở đi, **Câu lệnh Điều phối ở Mục 2 sẽ tự sinh ra** cho anh khi tới lượt — không cần liệt kê sẵn ở đây.

---

### ✅ HẠNG MỤC 1 — Chat 10: Citation Grounding

#### 🟦 Ô CODEX (dán vào ChatGPT/Codex — PHA 1: XÂY)

```
Bạn là Codex, builder của CRAVE. Trước khi viết code, đọc kỹ skill crave-codex-builder và toàn bộ ràng buộc cứng.

HẠNG MỤC: Chat 10 — Citation Grounding.
Mục tiêu: gắn mỗi khẳng định trong câu trả lời AI vào chunk_id cụ thể; khẳng định không có nguồn → gắn cờ grounded=false.

Làm theo PHA, DỪNG sau mỗi pha cho tôi xem, KHÔNG tự apply lên project bdttccztjtrcaztjgkot khi chưa được tôi xác nhận:

- PHA 1A: Viết migration 013_citation_grounding.sql (idempotent: dùng IF NOT EXISTS / DO-block kiểm pg_policies; thêm cột chunk_id, claim_text, grounded, citation_rank vào ai_query_sources; index; bật RLS + policy) KÈM file rollback 013_down.sql.
- PHA 1B: Sau khi tôi duyệt SQL, sửa workflow TKTL WF-02 (RAG Query): thêm yêu cầu trong prompt OpenAI bắt mỗi câu trích [chunk_id], output JSON {claims:[{text, chunk_id, grounded}]}; thêm node parse JSON đánh dấu claim không nguồn; INSERT vào ai_query_sources + audit_log (append-only). Dùng credential GMP-check + OpenAl, giữ Cách B verify JWT byte-identical.
- PHA 1C: Viết component frontend trong app/ (TS, shadcn): <CitationBadge> (xanh khi có nguồn, đỏ khi grounded=false) và <SourceList> resolve chunk_id → tên tài liệu + version.

Sau mỗi pha chạy checklist tự kiểm và in kết quả. TUYỆT ĐỐI không thêm credential thứ 3, không community node, không Variables, không crypto. Mọi giải thích tiếng Việt. Khi xong cả 3 pha, ghi "SẴN SÀNG BÀN GIAO CLAUDE CODE" kèm danh sách file đã tạo/sửa.
```

#### 🟩 Ô CLAUDE CODE (dán vào terminal Claude Code — PHA 2: KIỂM + SỬA)

```
Bạn là Claude Code, chốt chặn cuối của CRAVE. Codex vừa bàn giao hạng mục Chat 10 — Citation Grounding. Đọc kỹ skill crave-claude-reviewer.

1) Dùng MCP Supabase đọc schema THỰC TẾ project bdttccztjtrcaztjgkot (đối chiếu bảng ai_query_sources, document_chunks) và MCP n8n đọc workflow TKTL WF-02 — KHÔNG tin mô tả suông.
2) Chạy TOÀN BỘ 11 mục checklist, in bảng PASS/FAIL kèm bằng chứng (tên policy, tên node, số dòng). Đặc biệt kiểm: migration 013 idempotent + có rollback; mọi tool vẫn qua hybrid_search_v3 (không SELECT thô); audit_log chỉ INSERT; JWT Cách B byte-identical; citation grounding thật sự gắn chunk_id và gắn cờ claim không nguồn; không secret ở frontend.

Làm theo PHA:
- PHA 2A (REVIEW): chỉ đọc + báo cáo, CHƯA sửa. Liệt kê mọi FAIL + mức nghiêm trọng.
- PHA 2B (SỬA): sau khi tôi duyệt danh sách lỗi, sửa từng lỗi, ghi rõ đã sửa gì. KHÔNG apply migration / push git / sửa workflow production khi chưa có xác nhận "ĐỒNG Ý APPLY".

Quy tắc an toàn: nêu tên+ID trước khi đụng; không đổi đồng thời nhiều hệ thống; chạm dự án khác (BMS/VMP/QMS) thì DỪNG. Vi phạm ràng buộc cứng = FAIL TUYỆT ĐỐI. Tiếng Việt. Kết thúc bằng "PASS — SẴN SÀNG PRODUCTION" hoặc "FAIL — CẦN SỬA: [danh sách]".
```

#### 🟨 Sau khi PASS → dán **Câu lệnh Điều phối** (Mục 2) vào Claude Code để lấy hạng mục #2.

---

### ✅ HẠNG MỤC 2 — Chat 11: Eval Harness + Golden Dataset

#### 🟦 Ô CODEX (PHA 1: XÂY)

```
Bạn là Codex, builder của CRAVE. Đọc kỹ skill crave-codex-builder.

HẠNG MỤC: Chat 11 — Eval Harness + Golden Dataset.
Mục tiêu: mở rộng golden_questions từ 7 → 50–100 câu; xây pipeline chấm điểm tự động faithfulness/answer_relevancy/context_precision; ngưỡng pass ≥0.90, fail <0.80.

Làm theo PHA, DỪNG sau mỗi pha, KHÔNG apply khi chưa xác nhận:

- PHA 1A: Viết migration 014_eval_harness.sql (idempotent + rollback): bảng eval_runs, eval_results; mở rộng golden_questions nếu thiếu cột; bật RLS (chỉ vai trò QA/admin đọc).
- PHA 1B: Soạn 50–100 golden questions tiếng Việt phủ: happy path, edge case, câu đa bước, và ≥5 câu mà đáp án đúng là "không có thông tin". Mỗi câu kèm câu trả lời chuẩn + chunk nguồn mong đợi. Xuất dạng SQL INSERT idempotent.
- PHA 1C: Viết script eval (Python, chạy NGOÀI n8n — qua Claude Code/CI) dùng Ragas hoặc DeepEval, đọc key OpenAl từ biến môi trường (KHÔNG hardcode key). Pipeline: lấy golden_questions → gọi API CRAVE → chấm điểm → ghi eval_runs/eval_results.
- PHA 1D: Frontend trang /eval trong app/ hiển thị xu hướng faithfulness theo thời gian + so sánh prompt version.

Sau mỗi pha chạy checklist tự kiểm. Không credential thứ 3, không secret trong source. Tiếng Việt. Xong ghi "SẴN SÀNG BÀN GIAO CLAUDE CODE" + danh sách file.
```

#### 🟩 Ô CLAUDE CODE (PHA 2: KIỂM + SỬA)

```
Bạn là Claude Code, chốt chặn cuối của CRAVE. Codex vừa bàn giao Chat 11 — Eval Harness. Đọc skill crave-claude-reviewer.

1) Dùng MCP Supabase đối chiếu bảng eval_runs, eval_results, golden_questions trong project bdttccztjtrcaztjgkot.
2) Chạy 11 mục checklist + kiểm riêng: migration 014 idempotent + rollback; RLS giới hạn QA/admin; golden set có đủ 50–100 câu gồm ≥5 câu "không biết"; script eval KHÔNG hardcode key OpenAl (đọc từ env); ngưỡng pass/fail đúng (≥0.90 / <0.80).
3) Nếu có thể, chạy thử pipeline eval trên vài câu để xác nhận chấm điểm hoạt động.

PHA 2A (REVIEW) rồi PHA 2B (SỬA) như quy trình chuẩn. Không apply/push khi chưa xác nhận. Tiếng Việt. Kết thúc "PASS — SẴN SÀNG PRODUCTION" hoặc "FAIL — CẦN SỬA: [danh sách]".
```

#### 🟨 Sau khi PASS → dán **Câu lệnh Điều phối** (Mục 2).

---

### ✅ HẠNG MỤC 3 — Chat 12: Adaptive / CRAG Routing

#### 🟦 Ô CODEX (PHA 1: XÂY)

```
Bạn là Codex, builder của CRAVE. Đọc skill crave-codex-builder.

HẠNG MỤC: Chat 12 — Adaptive / CRAG Routing.
Mục tiêu: phân loại độ phức tạp truy vấn; câu đơn giản → gọi hybrid_search_v3 thẳng (nhanh/rẻ); câu phức tạp → vòng lặp đánh giá + truy hồi lại (có TRẦN max iterations).

Làm theo PHA, DỪNG sau mỗi pha:

- PHA 1A: Viết migration 015_query_routing.sql (idempotent + rollback): bảng query_complexity_log (câu hỏi, nhãn độ phức tạp, nhánh đã chọn, số vòng lặp); RLS.
- PHA 1B: Sửa workflow TKTL WF-02: thêm node phân loại (prompt few-shot OpenAl phân "đơn giản/phức tạp"); router phân nhánh; nhánh phức tạp có vòng đánh giá chất lượng chunk + truy hồi lại, TRẦN 5 vòng; mọi nhánh vẫn qua hybrid_search_v3; log vào query_complexity_log.
- PHA 1C: (tùy chọn) hiển thị nhánh đã chọn trên frontend cho minh bạch.

Checklist tự kiểm sau mỗi pha. Không credential thứ 3, không community node. Tiếng Việt. Xong ghi "SẴN SÀNG BÀN GIAO CLAUDE CODE" + danh sách file.
```

#### 🟩 Ô CLAUDE CODE (PHA 2: KIỂM + SỬA)

```
Bạn là Claude Code, chốt chặn cuối của CRAVE. Codex vừa bàn giao Chat 12 — Adaptive/CRAG Routing. Đọc skill crave-claude-reviewer.

1) MCP Supabase kiểm bảng query_complexity_log; MCP n8n đọc WF-02 đối chiếu thực tế.
2) Chạy 11 mục checklist + kiểm riêng: có TRẦN max iterations (chống vòng lặp vô hạn); mọi nhánh đi qua hybrid_search_v3 (không SELECT thô); migration 015 idempotent + rollback; router không phá Cách B verify; log đầy đủ mọi nhánh.

PHA 2A (REVIEW) rồi PHA 2B (SỬA). Không apply/push khi chưa xác nhận. Đặc biệt cảnh báo nếu vòng lặp có nguy cơ chạy quá trần hoặc tốn token bất thường. Tiếng Việt. Kết thúc "PASS — SẴN SÀNG PRODUCTION" hoặc "FAIL — CẦN SỬA: [danh sách]".
```

#### 🟨 Sau khi PASS → dán **Câu lệnh Điều phối** (Mục 2) để Claude Code tự sinh câu lệnh Hạng mục #4 (Chat 13 — AI Agent WF-12) và các hạng mục sau.

---

## 4. SƠ ĐỒ TỔNG (in ra dán cạnh máy)

```
        BẮT ĐẦU
           │
           ▼
   ┌───────────────┐   Codex xây    ┌───────────────┐
   │  Ô CODEX      │ ─────────────► │ "SẴN SÀNG BÀN  │
   │ (vào ChatGPT) │                │  GIAO..."      │
   └───────────────┘                └───────┬───────┘
                                            │
                                            ▼
   ┌───────────────┐  Claude kiểm   ┌───────────────┐
   │ Ô CLAUDE CODE │ ◄───────────── │   dán vào      │
   │ (vào terminal)│                │  Claude Code   │
   └───────┬───────┘                └───────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
   FAIL         PASS
     │           │
     │           ▼
     │   ┌─────────────────┐
     │   │ Dán CÂU LỆNH    │
     │   │ ĐIỀU PHỐI vào   │
     │   │ Claude Code     │
     │   └────────┬────────┘
     │            │
     │            ▼
     │   Claude tự cập nhật HandOFF
     │   + IN câu lệnh hạng mục KẾ
     │            │
     │            ▼
     │      HẠNG MỤC TIẾP THEO
     │            │
     └────────────┘ (nếu FAIL: gửi danh sách lỗi
        cho Codex sửa, rồi kiểm lại)
```

---

## 5. CHECKLIST NHANH MỖI NGÀY LÀM VIỆC

Trước khi mở phiên làm việc:
1. `cd ~/Desktop/Du_bao_thoi_tiet` rồi `claude` (đúng thư mục dự án).
2. Hỏi Claude Code: *"Đọc HandOFF, tôi đang ở hạng mục nào, câu lệnh kế tiếp là gì?"*
3. Làm đúng 1 hạng mục/phiên (giống "mỗi chat 1 mục" anh vẫn quen).
4. Hạng mục PASS → dán Câu lệnh Điều phối → nghỉ. Hôm sau tiếp tục từ bước 2.

---

## 6. CÀI 2 SKILL TRƯỚC KHI BẮT ĐẦU (làm 1 lần)

**Skill cho Claude Code** — dán vào Claude Code:
```
Tạo file .claude/skills/crave-claude-reviewer/SKILL.md với nội dung skill "crave-claude-reviewer" trong whitepaper (phần SKILL B). Sau đó xác nhận skill đã được nhận diện.
```

**Skill cho Codex** — mở một phiên ChatGPT, dán nội dung skill "crave-codex-builder" (phần SKILL A trong whitepaper) vào phần hướng dẫn/instructions của project, hoặc dán đầu mỗi phiên làm việc với Codex.

> Nội dung đầy đủ 2 skill nằm trong whitepaper "CRAVE GMP Validation Intelligence Platform: 2026 Technical Upgrade" — Phần E.

---

> **Nguyên tắc bất biến:** Codex xây trước, Claude Code chốt chặn cuối. Không bao giờ để hạng mục lên production khi Claude Code chưa báo PASS.
