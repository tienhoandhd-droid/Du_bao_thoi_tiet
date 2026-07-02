# CRAVE — Cổng quét đa engine TRƯỚC KHI DUYỆT (scan-before-approve)

> Bản thực thi của phương pháp "nhiều hình thức quét tài liệu trước khi duyệt"
> đã định trong §3.5 (đồng thuận đa engine) · R05-A06/A26/A29 · GĐ5.3 roadmap.
> Chốt 2026-07-02 theo chỉ đạo người dùng: **mọi tài liệu phải qua cổng này
> trước khi accession**; LAMSAFE (035) đã vào corpus mà CHƯA qua cổng → phải
> đưa vào hàng đợi review.

## 1. Vì sao

Accession 035 (LAMSAFE) dùng **một** engine (`n8n-extractFromFile-pdf`,
parse_quality 95) rồi ghi corpus. Đúng chỉ đạo: tài liệu GMP phải được **quét
bằng nhiều hình thức độc lập → đối chiếu đồng thuận → con người duyệt** trước khi
cho vào retrieval. Cổng này hiện thực hóa điều đó, chạy **local/on-device** để
không upload nội dung GMP lên cloud.

## 2. Công cụ: `scripts/ingest/crave_scan_gate.py`

Một script duy nhất (hợp nhất `r05_a06/a26/a29`), chạy trong venv nhẹ
(`pypdfium2` + `Pillow` + `pypdf`; OCR dùng Apple Vision compile từ
`scripts/r05_a26_macos_vision_ocr.m` bằng `clang`).

Mỗi trang mẫu chạy **3 hình thức quét ĐỘC LẬP** (khác nhà → khác kiểu lỗi):

| Engine | Nguồn | Ghi chú |
|---|---|---|
| `native` | PDF text-layer (pypdfium2) | born-digital; rỗng với ảnh scan → neo |
| `apple_vision` | Apple Vision OCR (on-device) | riêng tư, không lên cloud |
| `rapidocr` | RapidOCR/PP-OCR (ONNX) | **khác nhà Apple → độc lập thật** |

> v2 bỏ cách "accurate vs fast cùng Apple" (không độc lập). Có thể cắm thêm
> Tesseract/MinerU (cùng schema) làm engine thứ tư. Thang tăng chất lượng DPI
> `300→400→600` chạy tự động khi chưa đồng thuận (iterative consensus).

**Đồng thuận numeric/unit-aware:** so `SequenceMatcher` ratio (≥0,90) **và** yêu
cầu tập token số/đơn vị (m/s, µm, Pa, %, °C, CFU…) **khớp tuyệt đối** (numΔ=0).
Số sai một ký tự giữa hai engine ⇒ không đồng thuận (đúng tinh thần GMP).

**Trạng thái (không bao giờ auto-approve):**

| Status | Điều kiện |
|---|---|
| `PASS_CANDIDATE` | có text-layer + OCR khớp text-layer |
| `OCR_CONSENSUS_CANDIDATE` | ảnh scan; ≥2 pass OCR đồng thuận |
| `NEEDS_HUMAN_REVIEW` | bất đồng / lệch số / confidence thấp |
| `FAIL_EXTRACT` | không trích được nội dung |

Trạng thái tài liệu = trang tệ nhất trong mẫu. Mọi record giữ
`human_approved=false`, `ai_use_allowed=false`, `remote_mutation_allowed=false`.

## 3. Chạy

```bash
python3 -m venv .venv-scan
./.venv-scan/bin/pip install pypdfium2 Pillow pypdf
./.venv-scan/bin/python scripts/ingest/crave_scan_gate.py \
    "work/<file>.pdf" --code LV-BSC-A2 --pages 1,7,12 \
    --out work/crave_scan_gate_LV-BSC-A2.json
```

## 4. Kết quả kiểm chứng v2 (2026-07-02, apple_vision + rapidocr độc lập)

- **LV-BSC-A2 (LAMSAFE, đã ở corpus):** doc_status = `AL_ADJUDICATION`.
  - p1 `PASS_CANDIDATE` (native ~ apple sim 0,99).
  - p7 RETRY 300→400→600 (apple vs rapid sim ~0,57, lệch số) → **`AL_ADJUDICATION`**
    — đúng trang **bảng + sơ đồ** R05-A08 từng thấy bất đồng.
  - p12 RETRY×3 (native vs apple sim ~0) → `AL_ADJUDICATION` (trang nặng hình).
  - ⇒ LAMSAFE cần **AL so bản gốc + human QA** trang 7/12; cổng bắt đúng lỗ hổng.
- **PDA TR 39 (scan):** p3 apple~rapid dpi300=0,976 → dpi400=0,979 → **dpi600=0,985
  ⇒ `OCR_CONSENSUS_CANDIDATE`** (thang tăng DPI *giải quyết* bất đồng — đúng nhánh
  "quét lại/tăng chất lượng → đạt"). p5 sim ~0,73 không hội tụ → `AL_ADJUDICATION`.
- **CRAVE v2 MoA (kiểm chứng nhận định, cùng nguyên tắc):** execution SUCCESS —
  3 proposer free song song **bất đồng thật** (1 insufficient / 2 supported),
  aggregator OpenAI ra verdict `conditional` 0.68 grounded, ghi `claim_verdicts`.

## 5. Vị trí trong pipeline accession (v3 — AL duyệt tạm + hàng đợi cờ)

```
Drive PDF ─► [tải + hash sha256] ─► [SCAN GATE đa engine độc lập + DPI ladder]
   ├─ PASS/OCR_CONSENSUS ─► embed 1536 ─► migration promote (như 035)
   └─ AL_ADJUDICATION ─► [4] AL DUYỆT TẠM (provisional) → ĐI TIẾP (không nghẽn)
         └─ flag_payloads ─► INSERT public.scan_flag_queue
               (status AL_PROVISIONAL_PENDING_HUMAN, ai_use=true)
         └─ [5] người duyệt `scan_flags_pending` → clear_scan_flag():
               · HUMAN_APPROVED → BỎ CỜ   · HUMAN_REJECTED → thu hồi
   ─► cổng hybrid_search_v4 mở cho chunk đã duyệt
```

Backbone dữ liệu: migration `036_scan_flag_queue` (bảng + view `scan_flags_pending`
+ hàm `clear_scan_flag` chỉ admin/qa_manager). Đã apply live + verify vòng đời
đầy đủ (insert→pending→guard chặn non-QA→approve→bỏ cờ, pending=0).

## 6. Việc còn lại

1. Human QA (bỏ cờ) LAMSAFE p7/p12 qua `clear_scan_flag` (dashboard/WF-07).
2. (Nâng cấp) AL panel **free-vision MoA** đọc ẢNH GỐC (Gemini/Groq vision, song
   song độc lập) để adjudication giàu hơn — ghi cùng schema `scan_flag_queue`.
3. Panel dashboard hiển thị `scan_flags_pending` + nút duyệt/từ chối.
