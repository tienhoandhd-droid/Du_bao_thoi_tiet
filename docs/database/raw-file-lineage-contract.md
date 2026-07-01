# Raw-file Lineage Contract — CRAVE-026

- DB chỉ lưu metadata/lineage/hash; không lưu binary.
- `drive_sync_log.status='synced'` không chứng minh nội dung hoặc hash.
- Legacy Drive rows luôn `legacy_unverified` + `legacy_missing` cho tới khi worker
  đọc binary thật và tính SHA-256 64 hex lowercase.
- Chỉ `status=verified`, `hash_status=verified`, có `binary_sha256` và
  `verified_at` mới đủ điều kiện tạo immutable document version.
- `drive_file_id` là idempotency key; retry merge legacy IDs, không tạo duplicate.
- MIME/size/hash mismatch phải `rejected` hoặc `quarantined`, không vào parse queue.
- Không DELETE raw lineage qua application path; lifecycle dùng trạng thái.

## Legacy evidence

Live baseline: `gdrive_sources=0`; `drive_sync_log=4`, cả bốn có Drive ID và trạng
thái synced; `documents=12` nhưng 0 file hash/path/source URL/MIME. Migration 026
không backfill hash giả và không liên kết 12 documents khi chưa có evidence.

## Rollback

Tự động drop chỉ khi mọi row còn thuần legacy-unverified, không hash, không
source/document link mới. Sau verification hoặc consumer activation phải dùng
compatibility/roll-forward recovery.
