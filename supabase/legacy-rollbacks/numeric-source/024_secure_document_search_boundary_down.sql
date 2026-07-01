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
