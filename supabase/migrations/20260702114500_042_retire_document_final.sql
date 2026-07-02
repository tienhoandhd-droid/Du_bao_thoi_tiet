-- CRAVE deploy migration: 20260702114500_042_retire_document_final
-- Semantic source ID: CRAVE-042 / retire/reactivate: chỉ documents + chunks (giữ version bất biến)
-- Project: bdttccztjtrcaztjgkot
--
-- 040/041 cố cập nhật document_versions → bị (a) trigger bất biến CRAVE-027 và
-- (b) check constraint document_versions_index_status_check ('retired' không hợp lệ).
-- Cổng retrieval CHỈ phụ thuộc document_chunks.status. Nên retire tối giản:
--   documents.status=archived + approved_for_ai_use=false (hiển thị + reviewed),
--   document_chunks.status=archived (rớt cổng). document_versions GIỮ NGUYÊN
--   (bất biến — lineage trọn vẹn, đúng GMP). Reactivate đảo lại.

begin;

create or replace function public.retire_document(p_doc_id uuid, p_reason text default null)
returns public.documents
language plpgsql security definer set search_path = public, extensions
as $$
declare v_row public.documents;
begin
  if not public.user_has_any_role(array['admin'::public.user_role_name,'qa_manager'::public.user_role_name]) then
    raise exception 'retire_document: chỉ admin/qa_manager mới được ngừng sử dụng tài liệu.';
  end if;
  update public.documents
     set status='archived'::public.document_status, approved_for_ai_use=false,
         reviewed_by=auth.uid(), reviewed_at=now(), updated_at=now()
   where id=p_doc_id returning * into v_row;
  if not found then raise exception 'retire_document: không tìm thấy tài liệu %.', p_doc_id; end if;
  update public.document_chunks set status='archived'::public.document_status
   where document_id=p_doc_id and status <> 'archived'::public.document_status;
  return v_row;
end $$;

create or replace function public.reactivate_document(p_doc_id uuid)
returns public.documents
language plpgsql security definer set search_path = public, extensions
as $$
declare v_row public.documents;
begin
  if not public.user_has_any_role(array['admin'::public.user_role_name,'qa_manager'::public.user_role_name]) then
    raise exception 'reactivate_document: chỉ admin/qa_manager mới được kích hoạt lại.';
  end if;
  update public.documents
     set status='approved_for_ai_use'::public.document_status, approved_for_ai_use=true,
         reviewed_by=auth.uid(), reviewed_at=now(), updated_at=now()
   where id=p_doc_id returning * into v_row;
  if not found then raise exception 'reactivate_document: không tìm thấy tài liệu %.', p_doc_id; end if;
  update public.document_chunks set status='approved_for_ai_use'::public.document_status
   where document_id=p_doc_id and status='archived'::public.document_status;
  return v_row;
end $$;

commit;
