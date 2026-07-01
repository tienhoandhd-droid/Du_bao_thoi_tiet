-- CRAVE rollback artifact: 20260629110000_r01_search_documents_v1_down
-- Semantic source ID: CRAVE-024 / R01-A02 / R01-A05R
-- Legacy rollback artifact:
--   supabase/legacy-rollbacks/numeric-source/024_secure_document_search_boundary_down.sql
-- Original rollback SHA-256:
--   61f09070b0696930c951a8bd3fe327c52ee64a0c5f5fc47f5eab792d2ee717f7
--
-- CRAVE R01 / Rollback 024 — Secure document search boundary
--
-- Rollback này chỉ gỡ RPC search_documents_v1 nếu đúng artifact CRAVE-024.
-- Không sửa/xóa dữ liệu. Sau rollback, WF-06 mới không thể hoạt động; direct SQL
-- owner cũ KHÔNG được coi là trạng thái an toàn để republish lâu dài.
-- KHÔNG tự apply rollback nếu chưa có change-control và xác nhận riêng.

begin;

do $$
declare
  function_oid regprocedure := to_regprocedure(
    'public.search_documents_v1(text,public.document_type,public.source_type,public.language_code,public.document_status,text,text,text,public.translation_status,boolean,integer,integer)'
  );
  function_comment text;
begin
  if function_oid is null then
    return;
  end if;

  select obj_description(function_oid::oid, 'pg_proc')
  into function_comment;

  if function_comment is null or function_comment not like 'CRAVE-024:%' then
    raise exception 'CRAVE-024 rollback: function hiện có không mang marker CRAVE-024; từ chối drop artifact không xác định.';
  end if;

  drop function public.search_documents_v1(
    text,
    public.document_type,
    public.source_type,
    public.language_code,
    public.document_status,
    text,
    text,
    text,
    public.translation_status,
    boolean,
    integer,
    integer
  );
end
$$;

commit;
