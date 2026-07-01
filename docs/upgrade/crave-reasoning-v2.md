# CRAVE Reasoning v2 — Mixture-of-Agents + dịch chuyên ngành + trả lời tiến dần

> Nâng cấp phần **đầu ra** (quan trọng ngang truy xuất). Vấn đề v1: chuỗi tuyến tính Support→Refute→Judge,
> mỗi bước một model free gọi một lần → chất lượng/độ chi tiết trôi, "≈ một AI". Giải: MoA + aggregator mạnh
> + dịch DeepL glossary + câu trả lời tiến dần. Nguồn: MoA (arXiv 2406.04692, togethercomputer/moa),
> FunnelRAG (arXiv 2410.10293), Streaming RAG (2025), DeepL pharma glossary.

## M7 — Mixture-of-Agents (thay chuỗi tuyến tính)

**v1 (tuyến tính):** `Support(Gemini) → Refute(Groq) → Judge(Groq)` — mỗi lượt 1 model, lỗi/thiếu tích lũy.

**v2 (MoA — song song + tổng hợp):**
```
CONTEXT (bằng chứng đã truy xuất)
  ├─ Proposer A (Gemini)  → phân tích 2 chiều đầy đủ (support + refute/limiting + verdict nháp)  ┐
  ├─ Proposer B (Groq)    → phân tích 2 chiều đầy đủ (độc lập)                                     │ song song
  └─ Proposer C (HF)      → phân tích 2 chiều đầy đủ (độc lập)                                     ┘
        │  (mỗi proposer thấy CÙNG context, KHÔNG thấy nhau — đa dạng thật)
        ▼
  AGGREGATOR (OpenAI, 1 lượt mạnh) → hợp nhất 3 đề xuất:
     · gộp bằng chứng, khử trùng lặp, giữ trích dẫn EN gốc
     · Chain-of-Verification: tự đặt câu hỏi kiểm + trả lời trước khi chốt
     · verdict cuối (taxonomy GMP) + confidence + answer_vi CHI TIẾT
        │
  Self-consistency: nếu ≥2/3 proposer cùng verdict → tăng confidence;
     bất đồng mạnh → conflicting + requires_human_signoff
```

**Vì sao tốt hơn:** MoA khai thác tính "cộng tác" giữa model — mỗi model được đọc câu trả lời của model khác
(qua aggregator) cho ra chất lượng cao hơn tổng từng cái; chỉ dùng open-source đã vượt GPT-4o trên AlpacaEval.
Free lo **bề rộng** (nhiều góc nhìn), OpenAI lo **1 lượt tổng hợp chi tiết** → chất lượng đầu ra mà chi phí thấp.

**Vai trò model (đúng §0 roadmap):** proposer = free-tier (Gemini/Groq/HF); aggregator = OpenAI (1 call/câu).
Câu không tới hạn có thể để aggregator cũng là free (fallback) để tiết kiệm.

## M8 — Dịch song ngữ DeepL + glossary dược

- **DeepL API** (free 500k ký tự/tháng) thay LLM tự dịch: nhất quán thuật ngữ, có use-case dược phẩm.
- **Glossary DeepL** bơm từ bảng `glossary_terms` (VI↔EN) → ép dịch đúng: *worst-case, hold time,
  requalification, oil aerosol vs oil vapor…* Không để mỗi lượt LLM dịch một kiểu.
- Luồng: truy vấn **VI→EN** (trước retrieval) · đáp án **EN→VI** (giữ trích dẫn EN gốc song song).
- n8n: node DeepL (hoặc HTTP `api-free.deepl.com/v2/translate` + `glossary_id`). **Cần bạn tạo tài khoản
  DeepL API Free** → mình gắn credential + tạo glossary từ `glossary_terms`.
- Fallback khi hết quota: LLM-dịch có kèm glossary trong prompt.

## M9 — Câu trả lời tiến dần (FunnelRAG + streaming)

**Đánh giá ý tưởng "trả từng phần":** ĐÚNG hướng 2025–2026, nên làm 2 tầng:

1. **Retrieval coarse-to-fine (FunnelRAG):** xếp bậc theo `trust_level`/loại tài liệu.
   - Bậc 1 (chuyên luận dược điển, tiêu chuẩn ISO/GMP — trust cao) → chạy CRAVE trước, **trả verdict + tóm tắt ngay**.
   - Bậc 2 (SOP/report nội bộ), Bậc 3 (web/Tavily) → bổ sung bằng chứng **điền dần**, cập nhật verdict nếu đổi.
2. **UX streaming:** webhook `responseMode: streaming` (hoặc SSE) — tóm tắt hiện trước, bảng 2 chiều + nguồn khác chạy nền.

**Cảnh báo GMP (bắt buộc):**
- Câu trả lời nhanh (bậc 1) gắn nhãn **"tạm — đang bổ sung nguồn"** + DRAFT; vẫn phải grounded (không đoán).
- Nếu bậc sau làm **đổi verdict** (vd bậc 2 mâu thuẫn bậc 1) → hiện cảnh báo + đẩy `requires_human_signoff`.
- Không để nguồn web (bậc 3) chưa review lấn át nguồn chính thống (bậc 1).

## Thứ tự triển khai
1. **M7 MoA** (lõi chất lượng — làm trước, chạy được ngay với Gemini/Groq/HF + OpenAI aggregator).
2. **M8 DeepL** (cần tài khoản DeepL của bạn).
3. **M9 tiến dần** (sau khi retrieval thật mở khóa — R06 embedding).
