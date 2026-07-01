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

Mỗi trang mẫu chạy **≥3 hình thức quét độc lập**:

| Engine | Nguồn | Ghi chú |
|---|---|---|
| `native` | PDF text-layer (pypdfium2) | born-digital; rỗng với ảnh scan |
| `vision_accurate` | Apple Vision OCR 300 DPI, accurate | on-device, riêng tư |
| `vision_fast` | Apple Vision OCR 200 DPI, fast | pass đối chiếu chéo |

> Có thể cắm thêm Tesseract/PaddleOCR/MinerU (cùng schema record) khi cần engine
> OCR thứ hai độc lập cho tài liệu scan.

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

## 4. Kết quả kiểm chứng (2026-07-02)

- **LV-BSC-A2 (LAMSAFE, đã ở corpus):** doc_status = `NEEDS_HUMAN_REVIEW`.
  - p1 `PASS_CANDIDATE` (native ~ vision_accurate sim 0,99).
  - p7 `NEEDS_HUMAN_REVIEW` (native vs OCR sim 0,86; lệch 1 token số) — đúng là
    trang **bảng + sơ đồ** mà R05-A08 từng thấy engine bất đồng.
  - p12 `NEEDS_HUMAN_REVIEW` (native vs OCR sim ~0) — trang nặng hình.
  - ⇒ LAMSAFE cần **human QA lại các trang bảng/hình** trước khi coi là đã duyệt
    đầy đủ; cổng đã bắt đúng lỗ hổng.
- **PDA TR 39 (scan, không nằm corpus):** p3 hai pass OCR sim 0,98 nhưng lệch số
  ⇒ `NEEDS_HUMAN_REVIEW`; p5 sim 0,44 ⇒ review. Chứng minh nhánh OCR fail-closed.

## 5. Vị trí trong pipeline accession

```
Drive PDF ─► [tải + hash sha256] ─► [CRAVE SCAN GATE đa engine]
   ─► review record (human_approved=false)
   ─► CON NGƯỜI DUYỆT trên dashboard  ◄── bắt buộc, "trước khi duyệt"
   ─► chỉ record ĐÃ DUYỆT mới ─► embed 1536 ─► migration promote (như 035)
   ─► cổng hybrid_search_v4 mở cho chunk đã duyệt
```

## 6. Việc còn lại

1. Human QA lại LAMSAFE p7/p12 (bảng/hình) hoặc gắn cờ giới hạn.
2. (Tùy chọn) thêm engine OCR thứ hai độc lập (Tesseract/Paddle) cho tài liệu
   scan để có đồng thuận OCR mạnh hơn thay vì accurate-vs-fast cùng nhà Apple.
3. Ghi review record vào bảng hàng đợi Supabase + panel dashboard duyệt.
