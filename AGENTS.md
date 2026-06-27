# Codex instructions for CRAVE / Du_bao_thoi_tiet

Luôn trả lời bằng tiếng Việt.

Đây là repo CRAVE chính:
- Repo: tienhoandhd-droid/Du_bao_thoi_tiet
- Local path: ~/Desktop/Du_bao_thoi_tiet
- Frontend nằm trong app/
- Supabase project: bdttccztjtrcaztjgkot
- n8n: n8n.cpc1hn.com

## Skill mặc định

Với mọi task liên quan CRAVE, Supabase, n8n, migration SQL, workflow, frontend TypeScript, GMP, SOP, RAG hoặc audit trail, hãy tự áp dụng skill:

$crave-codex-builder

Không cần người dùng phải nhắc lại tên skill.

## Quy tắc an toàn

- Không apply_migration nếu chưa cho người dùng xem SQL và hỏi xác nhận.
- Không execute_sql ghi/sửa/xóa nếu chưa hỏi xác nhận.
- Không update/execute/publish/unpublish/archive workflow n8n nếu chưa hỏi xác nhận.
- Không push GitHub nếu chưa báo cáo diff và được xác nhận.
- Chỉ sửa workflow prefix TKTL.
- Không đụng workflow BMS-GMP, VMP, QMSTeam, GMP Kiểm Tạp.
- Không dùng project Supabase cũ xrpnlpfcoarouoqkhgfp.
- Không hard-code secret vào frontend/source code.

## Quy trình mặc định

1. Đọc cấu trúc repo.
2. Đọc file liên quan.
3. Kiểm tra git status.
4. Lập plan ngắn.
5. Sửa code.
6. Chạy test/lint/build nếu phù hợp.
7. Báo cáo kết quả và rủi ro.
