# Legacy numeric rollback artifacts

Thư mục này lưu rollback numeric/legacy từng nằm trong `supabase/rollbacks/`.
Chúng được giữ để phục vụ audit/source review, không tự động chạy.

Rollback live từ R01-A05R trở đi phải có file timestamped tương ứng với migration
deployable trong `supabase/rollbacks/`.

Không apply rollback legacy nếu chưa có exact recovery plan và approval riêng.
