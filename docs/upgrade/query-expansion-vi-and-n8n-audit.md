# Nghiên cứu: Mở rộng từ khóa tiếng Việt + Audit song song/kiểm tra n8n

## PHẦN A — Mở rộng truy vấn tiếng Việt (query expansion)

### A0. Hiện trạng (WF-02 RAG Query ĐÃ có expansion — nhưng đơn tuyến)
Chuỗi hiện tại (tuần tự, 1 nhánh):
`Verify JWT → Permission → **OpenAI Query Expansion** (1 call → embedding_query + fts_terms VI+EN) → Embed → hybrid_search_v3 (vector+FTS) → Rerank → Answer → Audit`
- **Điểm tốt sẵn có:** đã có expansion song ngữ (fts_terms gồm cả thuật ngữ Việt + Anh), fail-safe (lỗi → dùng query gốc), neo ý định (embed = gốc + mở rộng, tránh trôi nghĩa), có rerank.
- **Hạn chế:** chỉ **MỘT** biến thể truy vấn (single-shot). Nếu câu hỏi mơ hồ/đa nghĩa hoặc từ khóa VI khác cách diễn đạt trong tài liệu (VN hay dùng đồng nghĩa: "thẩm định/xác nhận giá trị sử dụng/validation"), một biến thể dễ **miss**. Chưa dùng nguyên tắc song song của hệ.

### A1. Kỹ thuật (khảo cứu 2025-2026)
| Kỹ thuật | Bản chất | Hợp CRAVE? |
|---|---|---|
| **Query Expansion** (synonym/thuật ngữ) | thêm từ đồng nghĩa/thuật ngữ EN↔VI | ✅ đã có, giữ |
| **Multi-Query** (3–5 biến thể song song) | LLM sinh N cách hỏi khác nhau → retrieve tất cả → hợp | ✅✅ **đúng nguyên tắc song song**, khuyến nghị thêm |
| **HyDE** (sinh câu trả lời giả rồi embed) | tốt cho câu hỏi ngắn/narrative | ⚠️ **YẾU cho số/định lượng** (GMP nhiều số) → chỉ dùng có điều kiện |
| **RRF fusion** | hợp nhiều bảng xếp hạng | ✅ đã có 1 phần trong hybrid_search_v3, mở rộng cho đa query |

Nghiên cứu chốt: *"Mature RAG không chọn 1 chiến lược mà thích ứng: query ngắn→HyDE, mơ hồ cao→Multi-Query, còn lại→Query Expansion"*; và *"expansion là baseline nhanh & thường tốt nhất; multi-query tăng bao phủ ý định"*.

### A2. Đề xuất cho hệ (đúng nguyên tắc song song + hợp tiếng Việt)
**Nâng "single-shot expansion" → "Multi-Query song song + RRF"** (tái dùng MoA-style):
1. **1 LLM call** sinh **N=3-4 biến thể tiếng Việt** (đồng nghĩa GMP: thẩm định/validation, hiệu chuẩn/calibration, độ kín/integrity…) + biến thể **thuật ngữ Anh** + 1 câu **mở rộng ngữ nghĩa**. (Rẻ: 1 call ra nhiều biến thể, không phải N call.)
2. **Embed song song** N biến thể → **hybrid_search mỗi biến thể song song** → **RRF hợp nhất** top-k (tái dùng đúng cơ chế RRF của hybrid_search_v4) → rerank → answer.
3. **Ưu tiên tiếng Việt:** thêm **từ điển đồng nghĩa GMP VI↔EN** (glossary) đưa vào prompt expansion + dùng cho FTS — giảm phụ thuộc LLM, ổn định, giải thích được. (Đã có glossary DeepL M8 — tái dùng/ mở rộng.)
4. **Fail-safe giữ nguyên:** lỗi expansion → về single query gốc.
5. **tsquery tiếng Việt:** đảm bảo FTS dùng `websearch_to_tsquery`/`plainto_tsquery` với cấu hình unaccent (bỏ dấu) để "thẩm định" khớp "tham dinh" — cần kiểm cấu hình FTS của hybrid_search_v4.

> Kết quả kỳ vọng: recall cao hơn cho câu hỏi VN đa cách diễn đạt, vẫn precision nhờ rerank + RRF; đúng nguyên tắc "song song, độc lập, tổng hợp".

---

## PHẦN B — Audit: n8n đã áp song song / kiểm tra chưa?

### B1. Bảng đánh giá theo workflow (17 active + 2 inactive)
| Workflow | Song song đa-engine? | Kiểm tra/verify? | Ghi chú |
|---|---|---|---|
| **CRAVE v2 MoA** (Dq7aO1y…) | ✅ 3 proposer song song (Gemini+2 Groq) | ✅ aggregator Chain-of-Verification + JWT + fallback | Chuẩn mực song song. Inactive (JWT-ready) |
| **AL Vision Panel** (6AIVN…) | ✅ Gemini+Groq đọc ảnh song song | ✅ aggregator + provisional + scan_flag_queue | Chuẩn mực. Active |
| **WF-02 RAG Query** | ⚠️ **KHÔNG** (expansion đơn tuyến) | ✅ JWT, permission, rerank, fail-safe, audit | **Ứng viên nâng cấp Multi-Query** |
| **WF-06 Document Search** | n/a (metadata search) | ✅✅ JWT→validate→RPC, 3 nhánh lỗi (Auth401/Validation/RPC), contract check, CORS pinned | Kiểm tra rất chắc |
| **WF-12/13** (QA/Copilot agentic) | ⚠️ tuần tự (AI Agent + tools) | ✅ embedding thật, memory | Có thể thêm multi-query khi gọi rag_search |
| **WF-14 Web Search** | ⚠️ Tavily 1 nguồn (đa domain) | ✅ trust-level, JWT, redact, audit | Đa nguồn nhưng không đa-engine song song |
| WF-01/07/09/10 (ingest/approve/sync) | pipeline tuần tự (đúng bản chất) | ✅ | Không cần song song |
| WF-03/04/05/11 (draft/check/calc/lit) | tuần tự | ✅ | — |
| WF-08 Health Monitor | n/a | ✅ | — |

### B2. Kết luận
- **Nguyên tắc song song ĐÃ áp ĐÚNG ở tầng suy luận/thị giác** (MoA + AL Vision) — nơi cần nhất, làm tốt.
- **CHƯA áp ở tầng RETRIEVAL** (WF-02, WF-12/13 rag_search): đây là **khoảng trống chính** và trùng đúng câu hỏi của người dùng — mở rộng từ khóa hiện là đơn tuyến.
- **Kiểm tra/verify:** hầu hết workflow có JWT + error-branch + audit tốt (WF-06 mẫu mực). Điểm cần bổ sung: **verify từng nhánh song song không trả rỗng** (đã lo cho AL; cần áp cùng nguyên tắc khi thêm Multi-Query — nếu 1 biến thể lỗi/empty thì RRF vẫn phải chạy với phần còn lại).

### B3. Cần nâng cấp thêm (ưu tiên)
1. **WF-02 → Multi-Query song song + RRF** (mục A2) — tác động lớn nhất tới "đáp án chuẩn hơn".
2. **Glossary GMP VI↔EN** dùng chung cho expansion + FTS (ổn định, giải thích được).
3. **Kiểm tra tsquery tiếng Việt** (unaccent) trong hybrid_search_v4.
4. **Áp cùng cơ chế cho WF-12/13** khi corpus đủ.
5. **Guard "nhánh song song rỗng"**: RRF/aggregator phải chịu được 1 ranker fail (giống AL panel size=0 vẫn ghi cờ).

> Lưu ý: các nâng cấp retrieval chỉ đo được hiệu quả khi **corpus đủ lớn** (hiện 1 tài liệu thật). Nên build cùng nhịp với nạp corpus (M-B).

## Nguồn
- Query Expansion survey (LLM era) — https://arxiv.org/pdf/2509.07794
- DMQR-RAG Diverse Multi-Query Rewriting — https://arxiv.org/pdf/2411.13154
- HyDE/Multi-Query/RRF production — https://medium.com/@mudassar.hakim/retrieval-is-the-bottleneck-hyde-query-expansion-and-multi-query-rag-explained-for-production-c1842bed7f8a
- RRF trong hybrid search — https://glaforge.dev/posts/2026/02/10/advanced-rag-understanding-reciprocal-rank-fusion-in-hybrid-search/
- Query rewriting improve recall — https://thegeocommunity.com/blogs/generative-engine-optimization/query-rewriting-multiquery-rag/
