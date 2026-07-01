# Đề xuất nâng cấp: Tìm kiếm tài liệu đa phương thức (tài liệu · hình · sơ đồ · bảng)

> **Loại:** đề xuất thiết kế. Nền kiến trúc: `docs/architecture/search-upgrade-master-plan.md`.
> Ràng buộc an toàn GMP: xem `README.md` (mục "Ràng buộc an toàn GMP"). Mọi thao
> tác live (apply migration / n8n publish / Git push) cần kiểm chứng trước khi bật production.

---

## 1. Mục tiêu

Người dùng (thẩm định nhà máy/thiết bị GMP) cần: khi tìm một nội dung, kết quả
trả về **không chỉ đoạn text**, mà **giống bản gốc tài liệu** — gồm:

- **Tài liệu nguồn** (mã, phiên bản, trang, đường dẫn về đúng vùng);
- **Hình ảnh** (picture) và **sơ đồ / lưu đồ** (diagram/flowchart) trích từ trang;
- **Bảng** (table) giữ nguyên cấu trúc hàng/cột;
- Hiển thị **cạnh crop trang gốc** để đối chiếu ("Xem bản gốc" side‑by‑side).

### "File gốc" tham chiếu
Yêu cầu này **đã được đặc tả** tại
[`docs/architecture/crave-multimodal-ingest-validation.md`](../architecture/crave-multimodal-ingest-validation.md)
— đặc biệt **§6 (Tables)** và **§7 (Figures/diagrams & visual similarity)**. Trích:

- `:5` — *"Applies to: scanned PDFs, tables, figures, diagrams and OCR‑derived text used by CRAVE"*
- `:140` — *"a `Xem bản gốc` control showing the exact page crop beside the structured table"*
- `:151‑152` — *"The dashboard must show the candidate table beside the source crop and mark engine‑disagreed rows/cells until a human reviewer resolves…"*
- `:160‑165` — *"For every accepted picture or diagram, preserve a private original crop and thumbnail, document version, page/bbox, binary hash, element class, OCR labels, caption and nearby context. Flowchart labels are validated as critical text; topology such as nodes, arrows and decision branches is stored separately…"*
- `:169‑172` — *"return a signed/private thumbnail reference, page citation and similarity score; allow the user to open the source‑page crop and the containing document."*

Đề xuất này **hợp nhất và cụ thể hóa** thiết kế sẵn có (R05‑A08/A09, R07‑A01/A02,
R08‑A01) thành một lộ trình thực thi có gate rõ ràng.

---

## 2. Khoảng cách hiện tại (vì sao chưa có)

- Retrieval hiện là **text‑first** qua `hybrid_search_v3`, đang **fail‑closed**
  (runtime count = 0). Chưa có Hybrid Search V4.
- Đầu ra bảng/hình/sơ đồ mới ở mức **thiết kế/source‑only**, chưa có schema,
  chưa có frontend, chưa ingest thật.
- Benchmark cho thấy trích **bảng/sơ đồ tự động không đáng tin** nếu thiếu human QA:
  R05‑A08 (page 7, tủ an toàn sinh học) — các engine cho shape mâu thuẫn
  (`14x4 / 13x4 / 9x4 / 8x4 / 17x6 / 17x2`), chỉ 2 đường line‑aware khớp `14x4`
  → chốt **`FAIL_CLOSED_REQUIRES_HUMAN_QA`**, không auto‑import.

➡️ Kết luận: đầu ra multimodal **bắt buộc đi qua staging + human QA**, không tô
màu/voting để tự duyệt.

---

## 3. Đặc tả ĐẦU RA tìm kiếm (kết quả trả về gồm gì)

Mỗi kết quả tìm kiếm là một **evidence bundle** có provenance đầy đủ:

```
SearchResult
├─ document: { document_code, source_type (REF-*), current_version_label, title }
├─ citation: { retrieval_log_id, chunk_id, document_version_id, page_start/end, section_path }
├─ scores:   { search_mode (hybrid|fts_only|visual|no_source), rrf_score, similarity }
├─ text:     đoạn chunk có căn cứ (chỉ claim gắn chunk_id hợp lệ)
├─ tables[]: { table_id, page, bbox, row×col matrix (đã QA), header/span/footnote,
│              source_crop_hash, engine_shape_matrix, disagreement_cells[],
│              review_badge }
├─ figures[]:{ figure_id, element_class (picture|diagram|flowchart|formula|chart),
│              page, bbox, thumbnail_ref (signed), crop_hash, caption, labels[],
│              topology (nodes/arrows/branches) — cho sơ đồ,
│              review_badge }
└─ source_view: { page_crop_ref (signed) }   ← để render "Xem bản gốc" side‑by‑side

review_badge = null                                   ← ảnh qua app quét (đồng thuận/rescan): KHÔNG nhãn
             | { text: "AL xét duyệt", reviewer, reviewed_at }   ← CHỈ khi AL_RESOLVED
```

Nguyên tắc đầu ra (fail‑closed):
- Chỉ trả **asset đã APPROVED** (đúng version/license/approval gate như text).
- Thiếu căn cứ → `search_mode = no_source`, **không bịa**, không biến web result
  thành SOP đã duyệt.
- Ảnh/bảng/sơ đồ luôn kèm **citation về trang gốc** và mở được **crop bản gốc**.
- **Chỉ ảnh/sơ đồ đã qua AL mới gắn nhãn `"✔ AL xét duyệt — <reviewer>"`** (ngay
  trên/dưới ảnh, hiển thị ở cả kết quả người dùng cuối lẫn dashboard QA). Ảnh/sơ
  đồ trích **tự động qua các app quét** (đồng thuận/rescan pass) **KHÔNG gắn nhãn**.

---

## 3.5. Chính sách trích xuất đa phương pháp & leo thang AL (CỐT LÕI)

> Theo chỉ đạo người dùng **2026‑07‑01**: vì trích bảng/sơ đồ tự động không đáng
> tin, mỗi phần tử (bảng, hình, sơ đồ, dòng OCR) phải được **quét bằng nhiều
> phương pháp độc lập** và xử lý theo 4 bước đồng thuận → leo thang dưới đây.
> Chính sách này là bản chốt của "resource‑aware multi‑engine/AL" ở R05‑A31 và
> Workflow‑P (R05‑A08/A09).

### Bước 1 — Quét đa phương pháp (bảo đảm **> 3 engine** cho mỗi phần tử)
- **OCR text:** Tesseract 5.5.2 · RapidOCR 1.4.4 · EasyOCR 1.7.2 (+ MinerU) → ≥4.
- **Bảng:** Docling/TableFormer · Camelot (lattice + stream) · pdfplumber · PaddleOCR PP‑Structure → ≥4.
- **Hình/sơ đồ:** bộ phát hiện crop + ≥3 đường đọc nhãn/topology.
- Mỗi engine là **một đường độc lập**; lưu output riêng của từng engine (`engine_values[]`).

### Bước 2 — Đồng thuận → PASS
- Nếu **> 3 engine cho kết quả GIỐNG NHAU** (khớp trong dung sai chuẩn hóa) →
  **PASS**, đánh dấu `extraction_status = CONSENSUS_PASS`.
- Định nghĩa "giống nhau" theo loại phần tử:
  - **Bảng:** cùng shape hàng×cột **và** cùng nội dung từng cell (chuẩn hóa khoảng trắng/đơn vị/dấu).
  - **OCR text:** cùng số / đơn vị / tham chiếu và thứ tự đọc.
  - **Hình/sơ đồ:** cùng nhãn (labels) **và** topology (node/mũi tên/nhánh).

### Bước 3 — Quét lại & nâng cao chất lượng (khi > 3 engine nhưng KHÁC NHAU)
- Nâng chất lượng quét: DPI **150 → 300 → 400**, khử nhiễu/lệch (denoise/deskew/
  binarize), render lại, mở rộng cửa sổ trang; lưu `rescan_params` đã dùng.
- Chạy lại Bước 2. Nếu bây giờ **> 3 engine giống nhau / đạt ngưỡng** → **PASS**,
  `extraction_status = RESCAN_PASS`.

### Bước 4 — Leo thang AL (khi vẫn KHÔNG ĐẠT)
- Chỉ chuyển **đúng những cell/vùng còn khác nhau** sang khâu **AL (người xét
  duyệt)**; phần đã đồng thuận **không** phải review lại (tiết kiệm công AL).
- **BẮT BUỘC — đính kèm chữ AL vào ô khác nhau:** giá trị do AL xét duyệt phải
  được ghi **đúng vào cell/vùng đã quét khác nhau**, kèm bằng chứng truy vết:
  - `resolved_value` — giá trị AL chốt;
  - `reviewer` (danh tính AL) + `reviewed_at`;
  - `engine_values[]` — mỗi engine đã cho gì (giữ nguyên để truy vết);
  - `extraction_status = AL_RESOLVED` — đánh dấu rõ "ô này do AL xét duyệt".
- Phần tử chỉ được `APPROVED_FOR_INDEXING` khi **mọi vùng khác nhau đều đã
  `AL_RESOLVED`** và mọi vùng còn lại là `CONSENSUS_PASS`/`RESCAN_PASS`.
- **Cấm** majority‑vote tự chốt; **cấm** auto‑approve số/đơn vị/cell bảng/nhãn sơ
  đồ GMP‑critical khi chưa qua AL.

### Sơ đồ quyết định
```
Quét ≥4 engine độc lập cho mỗi phần tử
  ├─ > 3 engine GIỐNG NHAU ─────────────────────────► CONSENSUS_PASS
  └─ > 3 engine KHÁC NHAU
        └─ quét lại + nâng chất lượng (DPI/denoise/deskew/window)
              ├─ đạt (>3 giống nhau) ───────────────► RESCAN_PASS
              └─ không đạt
                    └─ AL xét duyệt ĐÚNG vùng khác nhau
                          └─ đính kèm chữ AL + reviewer + engine_values ─► AL_RESOLVED
Phần tử APPROVED khi mọi vùng ∈ {CONSENSUS_PASS, RESCAN_PASS, AL_RESOLVED}
```

---

## 4. Kiến trúc pipeline end‑to‑end

Kết hợp các file kiến trúc sẵn có, tất cả **fail‑closed + human QA gate**:

```
Drive PDF (fileID + SHA‑256 tính NGOÀI n8n)          [heavy-document-processing-strategy]
   │  routing theo size (Light≤1MiB / Medium≤10 / Heavy≤50 / >50MiB), 1 file/exec, concurrency=1
   ▼
source_registry / raw_files  →  documents (REF-*)  →  document_versions (immutable)   [drive-native-dashboard-pipeline]
   ▼
Parse / OCR / Layout — ĐA ENGINE ĐỘC LẬP (≥4 đường, xem §3.5)                                   [mineru-scan-pipeline + multimodal-ingest-validation]
   ├─ OCR text:  Tesseract 5.5.2 · RapidOCR 1.4.4 · EasyOCR 1.7.2
   ├─ Table:     Docling/TableFormer · PaddleOCR PP‑Structure/img2table · pdfplumber/Camelot
   ├─ Figure/diagram detector (crop + bbox + hash + caption + topology)
   └─ MinerU crave-mineru-v1 (1 trong ≥3 đường; KHÔNG phải ground truth)
   ▼
Staging state machine — Workflow‑P (n8n/workflow-contracts/TKTL-Workflow-P-staging-review) [R05-A09]
   default production write = DENY  ·  áp dụng chính sách §3.5 cho từng cell/vùng
   ├─ >3 engine giống nhau        → CONSENSUS_PASS
   ├─ >3 khác nhau → quét lại/nâng chất lượng → đạt → RESCAN_PASS
   └─ vẫn khác     → READY_FOR_HUMAN_QA (AL) → đính chữ AL vào ô khác nhau → AL_RESOLVED
                     (KHÔNG majority vote; QUARANTINED nếu không giải quyết)
   ▼
Dashboard human QA — side‑by‑side (crop gốc | candidate) — reviewer ĐẠT/KHÔNG
   ▼
APPROVED_FOR_INDEXING  →  chunks (+ is_table/is_ocr/page/section) + table objects + figure crops
   ▼
Embedding recert (text: text-embedding-3-small 1536‑d)  +  image embedding (lane riêng)
   ▼
Retrieval:
   ├─ Text:   Hybrid Search V4 (FTS pool 30 + Vector pool 30 → RRF k=60 + boosts có version, RLS INVOKER)  [master-plan §4]
   └─ Visual: visual‑similarity lane RIÊNG (search asset đã duyệt, cùng license/version/approval gate)
   ▼
Citation grounding → Dashboard render (React, "Xem bản gốc")
```

Điểm bất biến của pipeline:
- **SHA‑256 tính ngoài n8n** (sandbox n8n khóa crypto); binary filesystem‑backed rồi drop ngay.
- **MinerU `llm-aided-config=false`** để chống data‑egress; model tải ở bước tooling riêng.
- Idempotency key ingest = `document_version_id + raw_sha256 + page_window + parser_lock_hash`.
- **Visual‑similarity tách khỏi text retrieval**, nhưng chịu **cùng** gate version/license/approval.

---

## 5. Bổ sung schema (đề xuất, chưa apply)

Nằm trong dải migration còn lại của kế hoạch (024–032), **cần Codex/approval để apply**:

- `document_chunks`: thêm cờ `is_table`, `is_ocr`, `page_start`, `page_end`,
  `heading_path`, `section_path` (đã dự kiến ở master‑plan §5.3).
- `document_tables`: `table_id`, `document_version_id`, `page`, `bbox_norm[0..1000]`,
  `cells jsonb`, `source_crop_hash`, `engine_shape_matrix jsonb`, `qa_status`,
  `reviewer`, append‑only evidence. **Mỗi cell** trong `cells` mang provenance
  đồng thuận (theo §3.5): `{ row, col, span, is_header, value, extraction_status
  (CONSENSUS_PASS|RESCAN_PASS|AL_RESOLVED), engine_values[], resolved_value,
  reviewer, reviewed_at, rescan_params }`.
- `document_figures`: `figure_id`, `document_version_id`, `page`, `bbox_norm`,
  `element_class`, `crop_hash`, `thumbnail_ref`, `caption`, `labels jsonb`,
  `topology jsonb`, `qa_status`. **Mỗi label/vùng** mang cùng bộ provenance
  `extraction_status / engine_values[] / resolved_value / reviewer / reviewed_at`
  như cell bảng, để đánh dấu vùng nào do AL xét duyệt.
- `visual_embeddings`: `figure_id`/`table_id` → vector (lane riêng), chỉ asset approved.
- `retrieval_log`, `retrieval_candidates`, `tool_call_log`: **append‑only** (đã có 030b/030c foundation).

Mọi thay đổi phải có **rollback + verify + test** tương ứng.

---

## 6. Dashboard "Xem bản gốc" (side‑by‑side)

Theo R05‑A09 handoff + multimodal §6/§7:

- **Panel trái:** render **crop trang gốc** (table crop / figure crop) + SHA‑256 + bbox.
- **Panel phải:** bảng candidate (ma trận đã QA) / metadata hình‑sơ đồ + engine
  shape matrix + danh sách cell mâu thuẫn.
- **Render bằng React** — **cấm chèn HTML thô từ engine** (chống XSS, đã có tiền lệ F4).
- Nút **Approve mặc định disabled**; chỉ bật khi reviewer giải quyết mâu thuẫn.
- Bảng: highlight cell mâu thuẫn; mỗi cell hiện **badge `extraction_status`**
  (CONSENSUS_PASS / RESCAN_PASS / **AL_RESOLVED**); cell `AL_RESOLVED` hiển thị
  rõ **"AL xét duyệt" + tên reviewer**, hover xem `engine_values[]` từng engine;
  export **CSV/XLSX chỉ từ ma trận đã duyệt**.
- Hình/sơ đồ: thumbnail signed + caption + labels; click mở **crop trang gốc** và tài liệu chứa nó.
- **Nhãn duyệt trên ảnh:** chỉ ảnh/sơ đồ qua **AL** gắn overlay **"✔ AL xét
  duyệt — <reviewer>"** (React, không HTML thô); ảnh trích tự động qua app quét
  **không gắn nhãn**. Áp dụng cả kết quả người dùng cuối lẫn dashboard QA.
- Trạng thái hiển thị: `Chờ review / Đã review / Sẵn sàng AI / Retired` (drive‑native §L46‑53).

---

## 7. Lộ trình thực thi theo pha

| Pha | Việc | Round liên quan | Điều kiện vào |
|---|---|---|---|
| **P‑0** | Hoàn tất R08‑A02: MinerU OQ 5 fixture (gồm fixture "sơ đồ có nhãn/mũi tên") trong môi trường cô lập | R08 | Đang chạy |
| **P‑1** | Nạp **corpus authoritative thật** (mapping `document_code → drive_file_id` hoặc corpus đã sửa) | R02/R03 | Có input authoritative (đang fail‑closed) |
| **P‑2** | Chạy Workflow‑P staging cho bảng + hình/sơ đồ → **human QA** duyệt | R05‑A08/A09, R07 | P‑0 + P‑1 |
| **P‑3** | Chunk + table object + figure crop → embedding recert (text) + image embedding | R05/R06 | P‑2 approved |
| **P‑4** | **Hybrid Search V4** (text) + **visual‑similarity lane** shadow → cutover | R06 | P‑3 |
| **P‑5** | Citation grounding + retrieval/tool evidence + **eval v2 release** | R07/R08 | P‑4 |
| **P‑6** | Dashboard "Xem bản gốc" side‑by‑side (React) | R07/R09 | P‑5 |
| **P‑7** | **R11 Final System Check → GO/CONDITIONAL GO/HOLD** | R11 | tất cả PASS |

---

## 8. Tiêu chí nghiệm thu (gate trước GO)

**An toàn (100% PASS):** permission leakage = 0 · không JWT → không retrieval ·
citation trỏ chunk/version tồn tại & được phép · asset trả về đều approved ·
secret scan 0 hit · source/live/manifest match.

**Chất lượng:** Hit@5 ≥ **96,55%** (baseline) · citation rate ≥95% ·
no‑source refusal ≥90% (mục tiêu 95%) · faithfulness ≥0,90.

**Multimodal riêng (theo §3.5):**
- Mỗi phần tử được quét bằng **> 3 engine độc lập**; lưu đủ `engine_values[]`.
- 100% cell/vùng trả về có `extraction_status ∈ {CONSENSUS_PASS, RESCAN_PASS, AL_RESOLVED}`.
- **0 vùng khác nhau nào được approve mà thiếu chữ AL đính kèm** (`AL_RESOLVED` phải có `resolved_value` + `reviewer` + `reviewed_at`).
- 100% bảng/hình/sơ đồ trả về có **source_crop_hash** + citation trang gốc; 0 asset chưa QA lọt vào kết quả (fail‑closed).
- Mọi bất đồng engine → quét lại → AL, **không** tự duyệt bằng majority‑vote.
- Reviewer (AL) sign‑off bắt buộc cho **số/đơn vị/cell bảng/nhãn sơ đồ** GMP‑critical còn bất đồng.

---

## 9. Ràng buộc bất biến

Fail‑closed / DENY mặc định · Human QA bắt buộc · AI chỉ DRAFT (không tự approve) ·
RLS thật (INVOKER, không owner/BYPASSRLS cho user‑facing) · Append‑only audit/
retrieval/tool · Chỉ `OpenAl` + `GMP-check` (không credential/AI trả phí thứ 3) ·
Chỉ workflow `TKTL`, không renumber 14 WF · Xử lý GMP **local/private** (cấm upload
cloud) · Không dùng regex HTML strip làm parser chính · Web result = ungoverned,
không thành citation governed · pgvector + Supabase là lõi (không thêm vector DB
tới khi đo giới hạn).

---

## 10. Bước kế tiếp & governance

- Ưu tiên ngay: (1) hoàn tất **R08‑A02** MinerU OQ; (2) cung cấp **corpus
  authoritative thật** để mở P‑1 (hiện là blocker input chính).
- Tài liệu nguồn: `docs/architecture/crave-multimodal-ingest-validation.md`,
  `crave-mineru-scan-pipeline.md`, `crave-heavy-document-processing-strategy.md`,
  `crave-drive-native-dashboard-pipeline.md`, `search-upgrade-master-plan.md`.
