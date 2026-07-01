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
| Embedding model | **`text-embedding-3-small` (OpenAI, cloud)** | always-on, rẻ; self-host embedding loại vì máy không 24/7 |
| LLM — tác vụ KHÓ (độ chính xác cao / phân tích) | **OpenAI** (gpt-4o-mini, nâng model khi cần) | công cụ cần chính xác, phân tích vấn đề, reasoning, sinh câu trả lời chính |
| LLM — tác vụ DỄ/phụ + vòng lặp kiểm | **Gemini / Groq / HF free tier** | query rewrite, HyDE, router, tóm tắt nháp, glossary; **lặp kiểm nhiều lượt/nhiều model free để tăng chính xác** |
| Reranker | **LLM-rerank qua API (free-tier)**, OpenAI cho câu khó — KHÔNG self-host | máy không 24/7 → dùng API |
| OCR/parse (BATCH ingest) | **Docling · PaddleOCR · Tesseract · MinerU** (local, free) | chạy trong khung giờ máy bật hoặc trên server n8n — không cần always-on |
| Visual retrieval | ~~ColPali/ColQwen self-host~~ **LOẠI cho runtime** (cần host 24/7) | chỉ xét lại nếu có server GPU always-on |
| Workflow | **n8n self-hosted** (đã có) | chỉ node/credential free |
| UI pattern | **Kotaemon**, **Perplexica/Fireplexity** (MIT/Apache) | học pattern, port React/TS |

### Chiến lược AI đã CHỐT (2026-07-01)

Thực tế: **máy không chạy 24/7** (chỉ bật một khoảng mỗi ngày) → runtime phải là **cloud** (n8n
server luôn bật). Bỏ Ollama/self-host always-on cho runtime.

**Phân tầng model (multi-AI):**
- **OpenAI (trả phí)** = **tác vụ KHÓ**: độ chính xác cao, phân tích vấn đề, reasoning, sinh câu trả
  lời câu khó, **embedding** (`text-embedding-3-small`).
- **Free-tier cloud** (Gemini/Groq/HF) = **tác vụ DỄ/phụ**: query rewrite, HyDE, router phân loại,
  tóm tắt nháp, glossary — và **dùng vòng lặp kiểm duyệt (nhiều lượt / nhiều model free) để tăng độ
  chính xác** thay cho một model mạnh trả phí.
- **KHÔNG dùng Claude** trong stack (đã loại).
- **Self-host free** (Docling/PaddleOCR/MinerU) = **chỉ batch ingest** trong khung giờ máy bật / trên server.

**Hai mẫu dùng AI:**

1. **Tác vụ khó → OpenAI trực tiếp** (một lượt, chất lượng cao): sinh câu trả lời câu khó, phân tích.

2. **Tác vụ dễ/phụ → free-tier + vòng lặp kiểm duyệt** (bù chất lượng bằng số lượt, vì free rẻ):
```
Tác vụ phụ (rewrite/HyDE/tóm tắt/kiểm citation)
   ─► free-tier sinh nháp
   ─► N vòng kiểm chéo bằng free-tier (nhiều lượt / nhiều model free), mỗi lượt 1 lens:
        · đúng dữ kiện (grounded)   · đủ citation   · đúng số/đơn vị
   ─► bất đồng? lặp tới khi hội tụ; nếu là nội dung GMP tới hạn → escalate OpenAI hoặc human sign-off
   ─► ghi mọi vòng vào audit append-only
```
Đây là mở rộng chính sách đồng thuận §3.5 (đa engine cho bảng/hình) lên **tầng câu trả lời**: câu rủi
ro cao ưu tiên OpenAI; phần phụ dùng vòng lặp free để đạt chính xác mà vẫn tiết kiệm.

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
|0.1| ✅ Chốt chiến lược AI (OpenAI tác vụ khó · free-tier + vòng lặp kiểm cho phụ; KHÔNG Claude) | — | ✅ xong | Đã ghi §0 |
|0.2| Tạo credential n8n free-tier phụ (Gemini/Groq/HF) + xác nhận credential OpenAI sẵn có | free tier | 🔵+🟡 | Credential n8n sạch, không hard-code |
|0.3| Xác định **khung giờ máy bật** cho batch ingest (OCR/parse/embedding corpus) | — | 🔵 | Lịch chạy batch |
|0.4| Kiểm extension free khả dụng trên Supabase (`pg_trgm`…) | Supabase | 🟢 | Danh sách extension |

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
|3.1| **Reranker qua API** (KHÔNG self-host): LLM-rerank bằng free-tier cho câu thường, **OpenAI cho câu độ chính xác cao** — chèn sau hybrid pool | 🟡 | +chính xác đo bằng eval |
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
|6.1| ~~ColPali/ColQwen self-host~~ **HOÃN** (cần host 24/7 — máy không luôn bật). Giữ OCR+text-embedding; xét lại nếu có server GPU always-on | 🔵 | — |
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
1. ✅ Chiến lược AI đã chốt (OpenAI cho tác vụ khó · free-tier + vòng lặp kiểm cho phụ; KHÔNG Claude).
2. Tạo free-tier account phụ (Gemini/Groq/HF) → đưa credential vào n8n (OpenAI đã có).
3. Xác định **khung giờ máy bật** cho batch ingest (OCR/parse/embedding corpus).
4. **Corpus thật** (mapping `document_code → drive_file_id`) để mở retrieval production.
