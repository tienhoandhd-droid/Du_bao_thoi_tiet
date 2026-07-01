# Nghiên cứu nâng cấp Tìm kiếm đa phương thức & Trải nghiệm (2026)

> Báo cáo deep-research (26 nguồn → 124 claim → 25 kiểm chứng đối nghịch → **24 xác nhận, 1 bác bỏ**).
> Bám ràng buộc CRAVE: Supabase pgvector · n8n (sandbox khóa crypto) · React/TS · **OpenAI-only**
> (không credential/AI thứ 3) · GMP fail-closed · human sign-off · output DRAFT. Ngày 2026-07-01.

---

## Kết luận nhanh

Có thể nâng cấp **mạnh** tìm kiếm mà **không cần dịch vụ AI thứ 3** nhờ tính năng gốc pgvector
(hybrid + RRF + nén embedding) và pattern UX mã nguồn mở. Phần "thị giác trang" (ColPali) mạnh
nhưng cần host model → để pha sau. Agentic RAG chính xác hơn nhưng chậm → chỉ dùng cho câu khó.

---

## 1. Tìm kiếm chính xác + đa phương thức

| Kỹ thuật | Hợp stack? | Tradeoff | GMP |
|---|---|---|---|
| **Hybrid FTS+vector + RRF** (`1/(k+rank)`, k≈60) | ✅ pgvector gốc (đã có `hybrid_search_v3`) | Thấp | ✅ trích dẫn rõ |
| **halfvec (16-bit)** giảm ~50% dung lượng | ✅ pgvector gốc | Gần như miễn phí, recall giữ | ✅ |
| **Binary quantization** (bit vector, ~32x nhỏ) | ✅ pgvector gốc | Cần **re-rank 2 tầng** (Hamming→cosine); phức tạp hơn | ✅ |
| **Reranking cross-encoder** (bge-reranker/ColBERT) | ⚠️ cần host model (hoặc VectorChord `max_sim` trong PG) | Tăng độ trễ; +chính xác | ✅ |
| **HyDE** (sinh doc giả định rồi embed) | ✅ gpt-4o-mini | +1 lệnh LLM/truy vấn; **rủi ro hallucination** → chỉ bật cho câu ngắn/mơ hồ | ⚠️ cần verify nguồn thật |
| **ColPali/ColQwen** (nhúng ảnh trang + MaxSim) | ❌ VLM tự host — **vi phạm OpenAI-only** | Rất tốn lưu trữ (~256KB/trang) + chậm query 10–50x | ✅ mạnh cho bảng/sơ đồ, nhưng pha sau |

> ⚠️ **Đính chính kỹ thuật:** "BM25" trên Postgres gốc là **không chính xác** — `ts_rank` chỉ dùng
> term-frequency (thiếu IDF + length-norm). Muốn BM25 thật cần extension `pg_search`/ParadeDB. Với
> corpus GMP nhỏ (<1M vector), RRF trên `ts_rank_cd` thường đã đủ.

## 2. Câu trả lời thông minh, chi tiết + phân tầng

- **Agentic RAG** (sub-query · giải nghĩa viết tắt · rerank · Summary Agent grounding): **+~8 điểm Hit@5**
  (62,35% vs 54,12%) nhưng **chậm ~6x** (5,02s vs 0,79s). → Dùng **adaptive routing**: câu đơn giản đi
  hybrid thẳng; câu phức tạp mới escalate agent (n8n AI Agent native) + human sign-off.
- **Citation grounding**: Summary Agent chỉ được phát biểu từ nội dung đã truy hồi ("composed strictly
  from retrieved content") — khớp yêu cầu DRAFT của GMP.
- **Faithfulness cấp mệnh đề** (statement-level) + **tool-specific attribution**: chuẩn đo hallucination
  & truy vết. Mượn **khái niệm**, dùng gpt-4o-mini làm judge đơn (KHÔNG bê stack judge đa mô hình).
- ❌ **Bị bác bỏ (0-3):** "sub-query trigger khi điểm truy hồi thấp là thành phần agentic hiệu quả nhất"
  → **đừng đầu tư nặng** vào riêng cơ chế này.

## 3. Ít dung lượng + tốc độ nhanh

- **halfvec** (mục 1) — quick win số 1 về dung lượng.
- **Semantic cache**: lưu embedding truy vấn + phản hồi, khớp cosine **≥0,8** trên HNSW → giảm **tới ~68,8%
  lệnh gọi LLM**. Chạy trên pgvector. ⚠️ GMP: phải **version-control cache theo `approved_for_ai_use`** để
  không phục vụ câu trả lời từ SOP đã hết hiệu lực; invalidate khi tài liệu deactivate.
- **Adaptive retrieval** + **streaming** + **small-model routing** (gpt-4o-mini mặc định, chỉ nâng model khó).

## 4. UX/Giao diện RAG (repo tham chiếu)

- **Kotaemon** (`github.com/Cinnamon/kotaemon`) — sát CRAVE nhất: hybrid+rerank, parsing đa phương thức
  chọn trên UI (Docling/PaddleOCR **local** — không cần dịch vụ trả phí), **trích dẫn inline + PDF viewer
  highlight vùng trích + điểm liên quan**. (Dùng Chroma/Milvus, không pgvector → học UX/kiến trúc, không drop-in.)
- **Perplexity-clone** (Fireplexity, Perplexica) — pattern "grounded & cited": mọi câu có nguồn, hover xem
  trước nguồn, streaming, câu hỏi gợi ý tiếp. Port pattern vào React/TS (gắn badge tin cậy + disclaimer DRAFT).
- Component: `assistant-ui`, `shadcn-chat` (awesome-shadcn-ui) — khớp React/TS + shadcn của CRAVE.

---

## Lộ trình nâng cấp đề xuất

### 🟢 Quick wins (hợp stack, an toàn GMP, làm trước)
1. **Hybrid V4 + RRF** (nâng `hybrid_search_v3` → 2 pool FTS+vector, RRF k=60) — đã nằm trong kế hoạch R06.
2. **halfvec** — migration đổi `vector(1536)` → `halfvec(1536)` (giảm ~50% dung lượng, recall giữ).
3. **Semantic cache** (pgvector, cosine≥0,8, version-controlled theo approved).
4. **UX trích dẫn** kiểu Kotaemon/Perplexity: câu trả lời **phân tầng** (tóm tắt → chi tiết → nguồn/bảng/hình),
   inline citation + hover preview + "Xem bản gốc" (đã có khung ở `MultimodalSearchPage`), streaming.
5. **Structured output phân tầng** từ gpt-4o-mini (summary/detail/citations) + badge độ tin cậy.

### 🟡 Nâng cấp trung bình
6. **Adaptive routing + Agentic RAG** cho câu phức tạp (n8n AI Agent) + human sign-off.
7. **HyDE** bật có điều kiện cho câu ngắn/mơ hồ (verify nguồn thật).
8. **Reranking** (LLM rerank shadow bằng gpt-4o-mini, hoặc VectorChord `max_sim` trong Postgres).
9. **Faithfulness eval cấp mệnh đề** (gpt-4o-mini judge) trong eval harness/CI.

### 🔴 Nâng cấp lớn (nghiên cứu/pha sau)
10. **Binary quantization** 2 tầng khi corpus lớn.
11. **ColPali/ColQwen** visual retrieval — **cần quyết định ngoại lệ OpenAI-only** (host VLM) hay giữ
    OCR local (Docling/PaddleOCR) + text-embedding. Với SOP thực tế, OCR+text-embedding thường đủ.
12. **ParadeDB/pg_search** cho BM25 thật (nếu `ts_rank` không đủ).

---

## Caveat & câu hỏi mở (cần eval nội bộ)

- Ràng buộc **OpenAI-only** là bộ lọc quyết định: ColPali + judge đa mô hình không tuân thủ nếu triển khai đầy đủ.
- Nhiều số liệu mạnh từ **preprint** (agentic fintech 85 QA; semantic cache domain lặp) → **chưa chứng minh cho GMP/dược**;
  phải A/B trên **golden dataset V/Q 58 câu** của CRAVE.
- Câu hỏi mở: agentic có giữ +8pt trên corpus GMP? · ngưỡng cosine cache cho GMP? · có host ColPali không? · cần BM25 thật không?

## Nguồn chính
pgvector (github.com/pgvector/pgvector) · Kotaemon (github.com/Cinnamon/kotaemon) · ColPali (arXiv 2407.01449) ·
Agentic RAG fintech (arXiv 2510.25518) · Faithfulness agentic (MDPI 9/12/309) · Semantic cache (arXiv 2411.05276) ·
HyDE (arXiv 2212.10496) · halfvec (neon.com, AWS) · Fireplexity/Perplexica.
