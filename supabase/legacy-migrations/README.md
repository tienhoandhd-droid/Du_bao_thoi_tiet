# Legacy numeric migration source artifacts

Thư mục này lưu các SQL numeric/legacy từng nằm trong `supabase/migrations/`.
Chúng là source/history artifacts, không phải deploy lane hiện hành.

Từ R01-A05R, `supabase/migrations/` chỉ chứa migration timestamped theo format
Supabase CLI để `supabase db push --linked --dry-run` không cố apply lại các
migration cũ.

Không xóa hoặc sửa các artifact legacy này nếu chưa có change-control riêng.
Khi cần mapping live timestamp ↔ semantic ID, xem:

- `docs/database/live-migration-ledger.md`

