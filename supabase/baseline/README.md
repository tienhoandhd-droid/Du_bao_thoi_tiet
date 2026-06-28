# Supabase baseline

Thư mục này lưu snapshot **chỉ đọc** của Supabase project `bdttccztjtrcaztjgkot`, được Claude Code thu thập qua MCP ngày **2026-06-29**.

Baseline dùng để đối chiếu source với trạng thái live khi lịch sử migration 001–012 không có file riêng trong repo. Đây không phải migration, schema dump hay script khởi tạo database.

## Quy tắc sử dụng

- Không chạy, không apply và không paste các file Markdown này vào SQL Editor.
- Không xem row count là dữ liệu cố định; đây chỉ là số đếm tại thời điểm snapshot.
- Không suy diễn policy, grant, trigger, signature hoặc function body từ danh sách tên. Những thuộc tính chưa có bằng chứng live phải được xác minh riêng.
- Không dùng baseline để thay thế migration source hoặc rollback đã được review.

## Nội dung

- `tables.md`: 33 bảng public, trạng thái RLS và row count tại thời điểm snapshot.
- `functions.md`: 19 function public tại thời điểm snapshot.

Nguồn: dữ liệu live do Claude Code lấy từ Supabase project `bdttccztjtrcaztjgkot` và chuyển cho Codex trong Chat 03. Snapshot này không thực hiện thay đổi nào lên Supabase.
