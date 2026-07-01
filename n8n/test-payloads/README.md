# n8n Test Payloads

Mỗi workflow/capability tạo fixture synthetic khi triển khai, gồm positive,
missing/invalid JWT, validation failure, permission denial, retry/backend failure
và idempotent replay nếu có write. Không lưu token/key hoặc production content.

Planned filenames nằm trong `docs/database/data-contract-matrix.md`.
