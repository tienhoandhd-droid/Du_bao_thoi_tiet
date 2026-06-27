# Gói review liên kết nền tảng CRAVE

Ngày lập: 2026-06-27  
Nhánh: `fix/platform-alignment-crave`  
Phạm vi hiện tại: **PHA 1A — Supabase security hardening**

## Mục tiêu

Đưa GitHub Pages, Supabase và n8n về cùng một cấu hình nền tảng trước khi tiếp tục
xây tính năng Chat 12–20. Gói này tập trung vào:

1. Ghi nhận đầy đủ lỗi đã phát hiện, hướng xử lý và cách xác minh.
2. Cung cấp migration 015 cùng rollback để Claude Code kiểm tra.
3. Theo dõi trạng thái từng pha, tránh nhầm giữa “đã sửa draft”, “đã publish” và
   “đã chạy production”.
4. Liệt kê chính xác các file nguồn đã tạo/sửa; không sao chép file nguồn thành
   nhiều bản gây lệch nội dung.

## Trạng thái thay đổi remote

- Supabase: **chưa apply migration**.
- n8n: **chưa update/test/publish/unpublish**.
- GitHub: **chưa push/commit/đổi Variables/Secrets**.

## Thứ tự Claude Code cần review

1. Đọc [`CHECKLIST.md`](./CHECKLIST.md).
2. Đọc [`PHA-1A-SUPABASE-REVIEW.md`](./PHA-1A-SUPABASE-REVIEW.md).
3. Mở các file nguồn trong [`FILE-MANIFEST.md`](./FILE-MANIFEST.md).
4. Dùng MCP Supabase **chỉ đọc** trên project `bdttccztjtrcaztjgkot` để đối chiếu:
   view, function ACL, policy, trigger và grants.
5. Chạy checklist PASS/FAIL trước khi đề nghị apply.

## Quy tắc review

- Không thao tác project cũ `xrpnlpfcoarouoqkhgfp`.
- Không apply SQL khi chưa có xác nhận của người dùng.
- Không update/publish workflow n8n ở PHA 1A.
- Không chạm workflow ngoài prefix `TKTL`.
- Nếu migration 015 được duyệt, các kế hoạch cũ đang dự kiến dùng số 015 phải
  chuyển sang 016 trở lên.

