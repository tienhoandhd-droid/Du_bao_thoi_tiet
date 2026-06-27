# WF-10 Google Drive — Quyết định hoãn (Chat 15) → Sẽ thực hiện ở Chat 16

## Cập nhật trạng thái — 2026-06-28

Lý do hoãn ban đầu (thiếu credential Google) đã được giải quyết: hệ thống hiện có
credential **`kết nối google`** (Google Service Account) trong n8n. WF-10 sẽ được
xây dựng tại **Chat 16** sử dụng credential này — không cần POC JWT inline.

---

## Lý do hoãn ban đầu (Chat 15)

CRAVE chỉ cho phép hai credential n8n:

1. `GMP-check` — Postgres, ID `0WcJFXEhwLXQhJmn`.
2. `OpenAl` — OpenAI, ID `r5CCCyYKeJDjnJ0A`.

Tích hợp Google Drive theo cách chuẩn cần thêm Google OAuth2 hoặc Google Service
Account credential trong n8n. Đây sẽ là credential thứ ba và vi phạm ràng buộc
cứng của hệ thống. Community node cũng không được phép sử dụng.

Môi trường n8n đồng thời chặn `require('crypto')` và `globalThis.crypto.subtle`,
nên không thể ký JWT thay thế trong Code node. Quyết định an toàn là hoãn WF-10.

## Phạm vi Chat 16

1. Xác nhận ID credential `kết nối google` qua MCP n8n.
2. Xác định scope Google Drive tối thiểu và thư mục được phép truy cập.
3. Thiết kế workflow prefix `TKTL`, Cách B byte-identical cho xác thực người dùng.
4. Migration 019 `drive_sync_log`: audit append-only, RLS `triggered_by = auth.uid()`.
5. Test lỗi, retry, idempotency, audit log append-only.
6. Cho người dùng xem workflow trước khi import, execute hoặc publish trên
   `n8n.cpc1hn.com`.

Private key service account không được đưa vào JSON workflow hay commit vào repo.
