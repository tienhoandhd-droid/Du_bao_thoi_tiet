-- CRAVE Chat 17 - Rollback Migration 020: phiên làm việc Validation Copilot.
-- Xóa bảng con trước bảng cha; index, policy, constraint và trigger phụ thuộc
-- sẽ được PostgreSQL xóa cùng bảng.

begin;

drop table if exists public.session_messages;
drop table if exists public.validation_sessions;

commit;
