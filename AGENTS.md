# Quy tắc Codex cho CRAVE / Du_bao_thoi_tiet

Luôn làm việc bằng tiếng Việt.

## Khi bắt đầu task code
- Ưu tiên dùng skill `$crave-codex-builder` nếu task liên quan CRAVE, Supabase, n8n, workflow, migration hoặc frontend.
- Đọc cấu trúc repo trước khi sửa.
- Kiểm tra `git status` trước khi sửa.
- Không làm trực tiếp trên main/master nếu task có thay đổi lớn; tạo branch riêng.

## GitHub
- Được phép sửa file local trong repo này.
- Trước khi commit phải hiển thị diff summary.
- Không merge PR nếu chưa được yêu cầu.

## Supabase
- Project đúng: `bdttccztjtrcaztjgkot`.
- Được phép đọc schema, list tables, xem migration.
- Trước khi chạy `apply_migration` hoặc `execute_sql` có ghi dữ liệu/schema, phải hiển thị SQL và hỏi xác nhận.
- Không dùng project cũ `xrpnlpfcoarouoqkhgfp`.

## n8n
- Server đúng: `n8n.cpc1hn.com`.
- Chỉ sửa workflow prefix `TKTL`.
- Không đụng workflow BMS-GMP, VMP, QMSTeam, GMP Kiểm Tạp.
- Trước khi `update_workflow`, `execute_workflow`, `publish_workflow`, `unpublish_workflow`, `archive_workflow`, phải mô tả thay đổi và hỏi xác nhận.

## Frontend
- Code nằm trong `app/`.
- Không hard-code secret.
- Chỉ dùng Supabase anon key nếu cần public config.
- Không dùng `innerHTML` cho dữ liệu từ DB nếu chưa escape.

## Kết thúc task
Luôn báo cáo:
- File đã sửa
- Supabase thay đổi gì
- n8n thay đổi gì
- Lệnh test/lint/build đã chạy
- Git status
- Commit message đề xuất
