-- Rollback migration 022: không có đủ bằng chứng để tái tạo chính xác definition cũ.
-- MANUAL RESTORE REQUIRED: sau khi DROP, phải phục hồi thủ công run_fts_eval_v1
-- phiên bản cũ dùng thứ tự kết quả theo document_code từ nguồn đã được xác minh.
--
-- CẢNH BÁO MẤT DỮ LIỆU / AUDIT TRAIL: rollback này không xóa các bản ghi đã được hàm ghi vào
-- eval_runs hoặc eval_results. Các bản ghi đánh giá hiện hữu được giữ nguyên để
-- bảo toàn audit trail; việc xử lý chúng cần một change-control riêng được phê duyệt.
DROP FUNCTION IF EXISTS public.run_fts_eval_v1(integer, text, text);
