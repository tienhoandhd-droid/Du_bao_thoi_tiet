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

## M8 — Dịch song ngữ (chiến lược quota-aware, DeepL chỉ là lớp phụ)

**Bối cảnh:** DeepL của user chỉ free ~1 tháng + 1 triệu ký tự. Giải: **không để DeepL làm xương sống.**
Khối lượng dịch trong CRAVE rất nhỏ (truy vấn + trích đoạn ngắn, KHÔNG dịch cả tài liệu), và phần lớn đã miễn phí.

**Dịch phân tầng (rẻ → đắt, dừng khi đủ tốt):**
1. **Glossary translation-memory (miễn phí, ưu tiên 1):** bảng `translation_cache` + `glossary_terms` — mỗi
   cụm từ/thuật ngữ chỉ dịch MỘT LẦN, lưu lại, tái dùng mãi. Thuật ngữ dược đã có trong glossary → tra bảng, 0 ký tự API.
2. **LLM + glossary (miễn phí, ưu tiên 2):** framing LLM ĐÃ sinh `claim_text_en`; aggregator ĐÃ xuất `answer_vi`.
   Đa số nhu cầu dịch được lo bằng free-tier sẵn có (Gemini/Groq) kèm glossary trong prompt.
3. **DeepL (quota, ưu tiên 3 — chỉ khi tới hạn):** chỉ gọi để **kiểm/chuẩn hoá thuật ngữ then chốt** (câu GMP
   rủi ro cao, số/đơn vị/tên tiêu chuẩn) — vài chục ký tự/lần. Kết quả cache vào `translation_cache` → không gọi lại.
4. **Fallback khi hết DeepL:** NLLB-200 qua **HF Inference** (miễn phí, đã có tài khoản HF) hoặc **LibreTranslate**
   self-host (không giới hạn) cho batch.

**Vì sao 1 triệu ký tự là "vô hạn" ở đây:** chỉ dịch truy vấn (~50–150 ký tự) và trích đoạn then chốt, lại được
`translation_cache` chặn trùng → thực tế tiêu vài nghìn ký tự/tháng. DeepL để dành cho việc quan trọng nhất: nhất quán
thuật ngữ chuyên ngành.

- n8n: HTTP `api-free.deepl.com/v2/translate` + `glossary_id` (credential DeepL của user). Glossary tạo 1 lần từ `glossary_terms`.
- **GMP:** trích dẫn luôn giữ EN gốc; bản dịch VI gắn nhãn "không chính thức".

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
