# Lộ trình nâng cấp Tìm kiếm đa phương thức — công cụ & AI MIỄN PHÍ

> Bám ràng buộc CRAVE + chỉ đạo 2026-07-01: **dùng công cụ/tài khoản miễn phí**, mọi AI bổ sung
> **chỉ bản miễn phí**. Nền: Supabase pgvector · n8n self-hosted · React/TS (Pages) · GMP fail-closed
> · human sign-off · output DRAFT. Nguồn kỹ thuật: `RESEARCH-search-ux-upgrade-2026.md`.
>
> Điểm cộng: free/self-host còn **an toàn GMP hơn** (chạy private, dữ liệu không rời hệ thống).

---

## 0. Chiến lược công cụ & AI miễn phí

| Vai trò | Chọn MIỄN PHÍ (khuyến nghị) | Ghi chú |
|---|---|---|
| Vector DB | **pgvector** (đã có) | free, không đổi |
| Hybrid/FTS/RRF | **Postgres FTS + pgvector** (đã có) | free, gốc |
| Nén embedding | **halfvec / binary** (pgvector) | free, gốc |
| Semantic cache | **bảng pgvector** | free, tự xây |
| Embedding model | **bge-m3** hoặc **multilingual-e5-large** (self-host Ollama/HF) *hoặc* giữ `text-embedding-3-small` | free self-host tốt cho song ngữ VI/EN; đổi model = re-embed + đổi chiều |
| LLM sinh câu trả lời | **Ollama local** (Qwen2.5 / Llama 3.x) — free + **private** ⭐ · hoặc **Google Gemini free tier** · **Groq free tier** | Ollama = tốt nhất cho GMP (không egress); free-tier cloud làm fallback |
| Reranker | **bge-reranker-v2-m3** (self-host, free) | tăng chính xác; cần chỗ chạy model |
| OCR/parse | **Docling · PaddleOCR · Tesseract** (local, free) | cho bảng/hình/sơ đồ |
| Visual retrieval | **ColPali/ColQwen** (weights free, self-host) | pha sau, cần GPU/RAM |
| Workflow | **n8n self-hosted** (đã có) | chỉ node/credential free |
| UI pattern | **Kotaemon**, **Perplexica/Fireplexity** (MIT/Apache) | học pattern, port React/TS |

**Quyết định hạ tầng AI free cần chốt (Giai đoạn 0):**
- **Phương án A — Ollama local (khuyến nghị GMP):** chạy model trên máy/server có thể reach từ n8n.
  Ưu: free tuyệt đối, private, không credential. Nhược: cần RAM/CPU-GPU; n8n phải gọi được endpoint Ollama.
- **Phương án B — Free-tier cloud API** (Gemini/Groq/HuggingFace): free hạn mức, không cần hardware.
  Nhược: dữ liệu rời hệ thống (cân nhắc GMP — chỉ gửi query + chunk đã duyệt public, không gửi tài liệu mật).
- **Phương án C — Giữ OpenAI** cho embedding (cực rẻ) + free cho phần còn lại (hybrid tiết kiệm).

---

## 1. Kiến trúc mục tiêu (tổng quan)

```
Truy vấn ──► [Semantic cache? ] ─hit─► trả lời cache (kiểm version approved)
   │ miss
   ▼
[Router adaptive]
   ├─ câu đơn giản ─► Hybrid V4 (FTS+vector, RRF) ─► rerank(free) ─► LLM(free) trả lời phân tầng
   └─ câu phức tạp ─► n8n AI Agent (free LLM) + tools(hybrid/glossary) ─► Summary+citation ─► human sign-off
   ▼
Đầu ra phân tầng: Tóm tắt → Chi tiết → Nguồn/bảng/hình (Xem bản gốc) + badge tin cậy + DRAFT
   ▼
[Faithfulness check cấp mệnh đề (free LLM judge)] ─► audit append-only
```

Multimodal ingest (song song): Drive → OCR/parse free (Docling/PaddleOCR/MinerU) → Workflow-P
staging → **đồng thuận đa engine → AL** → schema `document_tables`/`document_figures` → retrieval.

---

## 2. Lộ trình theo giai đoạn (chi tiết)

> Cột "Ai làm được": 🟢 làm ngay (Claude Code: Supabase CLI / frontend / GitHub) · 🟡 cần n8n (sau khi
> khởi động lại Claude Code để nạp n8n MCP, hoặc bạn import) · 🔵 cần bạn chốt/tạo tài khoản free.

### GIAI ĐOẠN 0 — Nền tảng & tài khoản free (1–2 ngày)
| # | Việc | Công cụ free | Ai làm | DoD |
|---|---|---|---|---|
|0.1| Chốt hạ tầng AI free (A/B/C ở §0) | — | 🔵 bạn quyết | Ghi quyết định |
|0.2| Tạo tài khoản/free-tier + credential n8n (Gemini/Groq/HF hoặc endpoint Ollama) | free tier | 🔵+🟡 | Credential n8n sạch, không hard-code |
|0.3| Đo tài nguyên máy (nếu Ollama/self-host) | `ollama`, htop | 🟢 | Biết chạy được model nào |
|0.4| Bật `pg_trgm`/kiểm extension khả dụng trên Supabase | Supabase | 🟢 | Danh sách extension free |

### GIAI ĐOẠN 1 — Quick wins retrieval (Supabase, free) — **ưu tiên cao**
| # | Việc | Ai làm | DoD / GMP gate |
|---|---|---|---|
|1.1| **halfvec**: migration `vector(1536)`→`halfvec(1536)` + rebuild HNSW | 🟢 CLI | Recall giữ; dung lượng −~50%; rollback có |
|1.2| **Hybrid V4 + RRF** (2 pool FTS+vector, RRF k=60, SECURITY INVOKER, RLS) | 🟢 CLI | Eval golden 58 câu ≥ baseline 96,55% |
|1.3| **Semantic cache** (bảng `semantic_cache` + cosine≥0,8 + cột `approved_snapshot`) | 🟢 CLI | Invalidate khi doc deactivate; append-only audit |
|1.4| Eval A/B (v3 vs v4) trên golden dataset | 🟢 | Báo cáo Hit@1/3/5, MRR |

### GIAI ĐOẠN 2 — UX câu trả lời phân tầng + trích dẫn (frontend, free) — **ưu tiên cao**
| # | Việc | Ai làm | DoD |
|---|---|---|---|
|2.1| Câu trả lời **phân tầng**: Tóm tắt → Chi tiết (expand) → Nguồn/bảng/hình | 🟢 | Render React thuần |
|2.2| **Inline citation + hover preview** + "Xem bản gốc" (đã có khung Multimodal) | 🟢 | Click → crop/nguồn |
|2.3| **Streaming** câu trả lời + **badge độ tin cậy** (CRAG) + disclaimer DRAFT | 🟢 | Deploy Pages |
|2.4| Port pattern Kotaemon (PDF highlight + relevance score) | 🟢 | — |

### GIAI ĐOẠN 3 — Reranking + HyDE (AI free)
| # | Việc | Ai làm | DoD |
|---|---|---|---|
|3.1| **Reranker free**: bge-reranker-v2-m3 (self-host) hoặc LLM rerank (free) — chèn sau hybrid pool | 🟡🔵 | +chính xác đo bằng eval |
|3.2| **HyDE có điều kiện** (free LLM sinh doc giả định) cho câu ngắn/mơ hồ | 🟡 | Chỉ bật khi query ngắn; verify nguồn thật |

### GIAI ĐOẠN 4 — Adaptive routing + Agentic + Faithfulness (n8n, free)
| # | Việc | Ai làm | DoD / GMP |
|---|---|---|---|
|4.1| **Router**: phân loại câu đơn giản/phức tạp → hybrid thẳng vs agent | 🟡 | Đo latency/cost |
|4.2| **Agentic** cho câu khó (n8n AI Agent + free LLM + tools) + **human sign-off** | 🟡 | Output DRAFT, citation bắt buộc |
|4.3| **Faithfulness cấp mệnh đề** (free LLM judge) trong eval/CI | 🟢🟡 | faithfulness ≥0,90 |

### GIAI ĐOẠN 5 — Multimodal ingest thật (free, local) — theo chính sách §3.5 đã chốt
| # | Việc | Ai làm | DoD |
|---|---|---|---|
|5.1| Hoàn tất **R08 MinerU OQ** (5 fixture) | 🟢 local | OQ pass |
|5.2| Schema **`document_tables`/`document_figures`/`visual_embeddings`** + cờ chunk (migration + rollback + test) | 🟢 CLI | RLS, append-only |
|5.3| **Workflow-P staging** (≥4 engine Docling/PaddleOCR/Tesseract/MinerU) → đồng thuận → AL | 🟡 | fail-closed, nhãn AL |
|5.4| Nối kết quả bảng/hình vào UI Multimodal (dữ liệu thật thay mẫu) | 🟢 | — |

### GIAI ĐOẠN 6 — Visual retrieval (nghiên cứu, tùy hardware)
| # | Việc | Ai làm | DoD |
|---|---|---|---|
|6.1| Thử **ColPali/ColQwen** self-host (weights free) nếu có GPU/RAM; else giữ OCR+text | 🔵 | Quyết định pha sau |
|6.2| **Binary quantization** khi corpus lớn (2 tầng rerank) | 🟢 CLI | Recall −<4% |

### GIAI ĐOẠN 7 — Cổng GO (R11)
Release manifest + eval đạt ngưỡng + security gate 100% + human sign-off → GO/CONDITIONAL GO.

---

## 3. Thứ tự ưu tiên (nếu làm tuần tự)
**Tuần 1–2:** GĐ0 → GĐ1 (halfvec, Hybrid V4+RRF, semantic cache) — *tác động cao, an toàn, làm ngay.*
**Tuần 2–3:** GĐ2 (UX phân tầng + trích dẫn + streaming) — *người dùng thấy ngay.*
**Tuần 3–4:** GĐ3–4 (rerank, HyDE, routing, agentic, faithfulness).
**Tuần 4–6:** GĐ5 (multimodal ingest thật).
**Sau:** GĐ6–7 (visual, GO).

## 4. Ngưỡng chất lượng (giữ nguyên)
Hit@5 ≥ 96,55% (baseline) · citation rate ≥95% · no-source refusal ≥90% · faithfulness ≥0,90 ·
permission leakage=0 · secret scan 0. Cấm sửa số để "làm xanh".

## 5. Governance khi triển khai
- Mọi thao tác live (migration/n8n publish/git push) theo quyền build hiện tại (Claude Code toàn quyền
  giai đoạn xây; siết lại sau). Vẫn secret-scan + verify trước push; tài liệu bản quyền/PDF không lên public.
- Credential free: lưu trong n8n, không hard-code, không commit.
- Mọi AI output GMP = DRAFT; human sign-off bắt buộc; audit append-only.

## 6. Việc cần BẠN quyết/chuẩn bị
1. **Chốt hạ tầng AI free** (A: Ollama local / B: free-tier cloud / C: giữ OpenAI + free) — §0.
2. Nếu chọn B: tạo free-tier account (Gemini/Groq/HF) → đưa credential vào n8n.
3. Nếu chọn A: xác nhận máy/server chạy Ollama mà n8n gọi được.
4. **Corpus thật** (mapping `document_code → drive_file_id`) để mở retrieval production.
