-- Rollback CRAVE Chat 11 - Migration 014: bộ nhớ hội thoại WF-12
-- Xóa bảng sẽ tự xóa index, constraint và policy phụ thuộc.

begin;

drop table if exists public.chat_memory;

commit;

