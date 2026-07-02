# Nghiên cứu: Lưu hình/sơ đồ/bảng ở Supabase & hiển thị trên dashboard GitHub Pages

> Mục tiêu: trích **hình ảnh / sơ đồ / bảng** từ tài liệu (nhất là bản scan) → lưu
> Supabase → **hiển thị trên dashboard GitHub Pages** (tĩnh, repo public, anon key
> bị bake vào bundle). Bản quyền GMP → phải riêng tư, không rò rỉ.

## 0. Ràng buộc thực tế (từ khảo codebase)
- Dashboard là **site tĩnh** (Vite, base `/Du_bao_thoi_tiet/`), deploy GitHub Pages; **anon key nằm trong bundle công khai** (public-safe). ⇒ **Mọi bảo mật phải dựa vào RLS Supabase + signed URL**, TUYỆT ĐỐI không service_role ở frontend (đã có test chặn `App.tsx:474`).
- Client Supabase: anon key + **session JWT** (`signInWithPassword`/`getSession`); `sb.storage.from(bucket).createSignedUrl()` chạy dưới JWT này và bị RLS `storage.objects` chi phối. Hiện **chưa dùng Storage, chưa có bucket**.
- UI multimodal (`MultimodalSearchPage.tsx`) hiện là **mock**, nhưng đã định sẵn shape: `DocumentFigure{elementClass: picture|diagram|flowchart|formula|chart, page, caption, labels[], alReviewer, bbox, sha256}`, `DocumentTable{page, rows, cols, cells[]}`. ⇒ Schema thật nên khớp shape này.
- `document_chunks` có `page_number` nhưng **không có bbox** → cần bảng mới để gắn hình↔vùng trang.

## 1. Lưu Ở ĐÂU: Supabase Storage, KHÔNG nhồi vào Postgres
| Dữ liệu | Nơi lưu | Lý do |
|---|---|---|
| **Ảnh crop** hình/sơ đồ (webp) | **Supabase Storage** (private bucket) | S3-backed, CDN, không phình DB, hỗ trợ signed URL + (Pro) resize |
| Metadata (page, bbox, class, caption, sha) | Bảng `document_figures` | truy vấn/lọc/gate RLS |
| **Bảng số liệu** | `document_tables.cells jsonb` + `markdown` | render HTML + giữ **số liệu** để tra cứu; kèm crop ảnh (đối chiếu) |
| (sau) visual embedding CLIP | `document_figures.visual_embedding vector(768)` | multimodal search "tìm bằng mô tả/ảnh" |

**Không** lưu ảnh dạng `bytea`/base64 trong Postgres: nặng, chậm, tốn egress, phá cache CDN.

## 2. Bucket + Bảo mật (RLS) — điểm mấu chốt cho GitHub Pages
- Tạo **bucket private** `doc-figures` (`public=false`). Ảnh KHÔNG có public URL.
- Path quy ước: `{document_code}/{version}/p{page}/{figure_id}.webp` (+ `..._thumb.webp`).
- **RLS trên `storage.objects`** (signed URL kế thừa RLS, kiểm tại lúc *tạo* URL):
  ```sql
  create policy "figures_read_authenticated"
  on storage.objects for select to authenticated
  using ( bucket_id = 'doc-figures' );
  ```
  Đủ cho nhóm nội bộ <10 người đã đăng nhập. Chặt hơn (gate theo tài liệu đã duyệt) →
  không join `documents` trực tiếp trong RLS storage được → dùng **Edge Function**
  tạo signed URL sau khi kiểm `documents.approved_for_ai_use`, hoặc tách path theo
  trạng thái. Giai đoạn đầu: policy authenticated là đủ + an toàn (khách vãng lai
  KHÔNG đăng nhập ⇒ không tạo được signed URL ⇒ không rò rỉ).
- **Hiển thị**: frontend gọi `createSignedUrl(path, 3600)` (hoặc `createSignedUrls` hàng loạt) dưới JWT session → `<img src={signedUrl}>`. base path `/Du_bao_thoi_tiet/` không ảnh hưởng (URL Supabase là tuyệt đối).
- **Upload**: CHỈ từ server-side (n8n service_role / local gate), không từ frontend.

## 3. Thumbnail: image-transform là Pro-plan → PRE-GENERATE lúc ingest
Supabase resize-on-the-fly (`?width=..&height=..`, endpoint `/render/image/`) **chỉ có từ gói Pro**. Để **không phụ thuộc gói**, ingest **tạo sẵn 2 bản**: `full.webp` + `thumb.webp`. Dashboard lưới hiển thị thumb (nhẹ), click mở full. (Nếu lên Pro thì bật transform để tiết kiệm.)

## 4. Schema đề xuất (khớp UI mock)
```
document_figures(
  id uuid pk, document_id uuid, document_code text, document_version text,
  page_number int, figure_index int,
  element_class text check in (picture,diagram,flowchart,formula,chart,table),
  bbox jsonb,               -- {x,y,w,h} theo toạ độ trang chuẩn hoá
  storage_path text, thumb_path text,
  caption text, labels text[], ocr_text text,
  source_sha256 text, crop_sha256 text,          -- provenance + chống trùng crop
  detected_by text[],       -- engine phát hiện (đa engine)
  review_status text,       -- consensus / al_provisional / human_approved
  al_reviewer text, visual_embedding vector(768) null,
  created_at timestamptz default now(),
  unique(document_code, document_version, page_number, figure_index)
)
document_tables( ... page_number, n_rows, n_cols, cells jsonb, markdown text,
  storage_path text null, review_status, source_sha256, ... )
```
+ **view** `document_figures_v` (RLS `security_invoker=on`, gate theo documents.approved) cho dashboard đọc; + unique để **chống trùng crop** (theo `crop_sha256`).

## 5. Trích hình (ingest) — hybrid local/cloud, đa engine
- **Local (máy mở, ưu tiên):** `PyMuPDF` lấy ảnh nhúng + bbox; `Docling`/`PP-Structure` (layout) tách figure/table/formula regions; Apple Vision OCR caption/nhãn; render crop → webp.
- **Cloud (máy tắt, n8n):** Gemini vision (nhận PDF trực tiếp) phát hiện vùng hình + bbox + caption; crop qua render API.
- **Nguyên tắc đa engine** (như scan text): ≥2 engine phát hiện → hợp vùng; lệch → AL đối chiếu ảnh gốc → cờ chờ human (tái dùng `scan_flag_queue` + AL panel vision).
- Upload crop (full+thumb) lên bucket → insert `document_figures`.

## 5b. NHẬN BIẾT CÓ HÌNH (figure detection) — 2 ca
- **Born-digital PDF**: `PyMuPDF page.get_images()` trả ảnh nhúng + bbox **trực tiếp, chắc chắn**. (Sơ đồ vẽ vector → cần layout model như dưới.)
- **Bản scan (cả trang là 1 ảnh)**: dùng **layout-detection model** phát hiện VÙNG và phân loại figure/table/formula + bbox:
  - Local (máy mở): **Docling** (bbox texts/tables/pictures), **Surya** (layout + table, 90+ ngôn ngữ — có tiếng Việt), hoặc **PP-Structure/PP-DocLayout**.
  - Cloud (máy tắt, n8n): **Gemini vision** — prompt "liệt kê mọi hình/sơ đồ/bảng trên trang + bbox + mô tả".
  - **Đa engine ≥2** → hợp vùng theo IoU; lệch → **AL** đối chiếu ảnh gốc → cờ chờ human. Rồi crop theo bbox → webp (full+thumb) → Storage.

## 6. Hiển thị & tra cứu trên dashboard
- `MultimodalSearchPage` (bỏ mock): đọc `document_figures_v` → lưới thumb (signed URL) + caption/nhãn + badge review_status; click → ảnh full + bbox overlay trên trang gốc.
- `FlagQueuePanel v2`: hiện **crop trang gốc** (signed URL) cạnh 3 cột OCR (apple/rapid/AL) + mismatch → QA đối chiếu trực tiếp.

## 6b. TÌM BẰNG CHỮ RA HÌNH (text → image retrieval) — 3 lớp, đề xuất hybrid
- **Lớp 1 (NỀN TẢNG, đề xuất chính) — Caption/description embedding (text→text):**
  lúc ingest, vision model **mô tả hình bằng chữ** ("Sơ đồ dây chuyền chiết rót vô
  trùng cấp A…") + **OCR nhãn/chữ trong hình** + caption gốc + đoạn văn quanh hình.
  Nhúng mô tả này bằng **CHÍNH model text 1536 đang dùng** → đưa vào index như một
  "chunk hình". Gõ chữ → query khớp mô tả → **hình hiện ra**. Ưu: tái dùng
  `hybrid_search_v4` sẵn có, **hợp tiếng Việt**, **giải thích được** (mô tả là chữ),
  rẻ, không thêm model. → Đây là cách chắc nhất, làm trước.
- **Lớp 2 (LUÔN NÊN CÓ) — Liên kết hình ↔ trang/chunk:** mỗi figure gắn `page_number`
  + chunk cùng trang. Khi CRAVE trích dẫn đoạn ở trang X → **kèm luôn hình ở trang X**.
  Không cần embedding hình, rất hiệu quả cho tài liệu kỹ thuật.
- **Lớp 3 (NÂNG CAO, bật sau) — Embedding đa phương thức thật (visual):** nhúng CHÍNH
  ẢNH vào cùng không gian với chữ để bắt cái caption bỏ sót. Lựa chọn:
  **Gemini Embedding 2** (2026, native multimodal, 100+ ngôn ngữ — hợp tiếng Việt,
  cloud/tốn phí) hoặc **CLIP/SigLIP** (local, miễn phí nhưng yếu tiếng Việt + yếu
  hình dày chữ). Lưu ở `document_figures.visual_embedding vector(768)`.
- **Best practice** (theo nghiên cứu): "dual representation" (chữ-trên-hình + visual)
  cho kết quả tốt nhất; nhưng **bắt đầu bằng Lớp 1 + Lớp 2 là đủ dùng** và đúng
  nguyên tắc explainable của CRAVE. Lớp 3 thêm khi cần "tìm visual thuần".

## 7. Chi phí / giới hạn
- Storage dung lượng + egress (signed URL qua CDN, cache theo tham số).
- Image transform Pro-only → **pre-gen thumb** (đã chọn).
- CLIP embedding = giai đoạn sau (không chặn phần lưu+hiển thị).

## 8. Lộ trình build (đề xuất)
1. **Migration**: `document_figures` + `document_tables` + view RLS + tạo bucket `doc-figures` + policy `storage.objects`. (chống trùng crop bằng `crop_sha256`).
2. **Ingest trích hình**: local (PyMuPDF/Docling) + cloud (Gemini) → upload + insert; đa engine + AL cho vùng lệch.
3. **Frontend**: `MultimodalSearchPage` thật (signed URL) + `FlagQueuePanel v2` (crop trang).
4. **Sau**: visual embedding CLIP + multimodal search.

## Nguồn
- Supabase Storage fundamentals / access-control / serving — https://supabase.com/docs/guides/storage
- RLS storage.objects + `storage.foldername()` — https://supabase.com/docs/guides/storage/security/access-control
- Image transformations (Pro-plan) — https://supabase.com/docs/guides/storage/serving/image-transformations
- Deep dive (bucket design, signed URLs, RLS) — https://dev.to/kanta13jp1/supabase-storage-deep-dive-bucket-design-signed-urls-image-transforms-and-rls-3b9k
- pgvector + CLIP multimodal — https://supabase.com/docs/guides/ai/examples/image-search-openai-clip
