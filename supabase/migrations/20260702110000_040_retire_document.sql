-- CRAVE deploy migration: 20260702110000_040_retire_document
-- Semantic source ID: CRAVE-040 / vòng đời tài liệu: ngừng sử dụng (hết hạn) + kích hoạt lại
-- Project: bdttccztjtrcaztjgkot
--
-- "Xóa tài liệu hết hạn" đúng GMP = NGỪNG SỬ DỤNG (retire), KHÔNG hard-delete:
--   documents.status='archived' + approved_for_ai_use=false,
--   document_chunks.status='archived' (rớt khỏi cổng hybrid_search),
--   document_versions.index_status='retired' + approved_for_ai_use=false.
-- Giữ nguyên version/chunk/audit để truy vết. Có reactivate để hoàn tác.
-- Chỉ admin/qa_manager (SECURITY DEFINER + role guard, như clear_scan_flag).

begin;

do $guard$
begin
  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-040: thiếu user_has_any_role.';
  end if;
  if to_regclass('public.documents') is null or to_regclass('public.document_chunks') is null then
    raise exception 'CRAVE-040: thiếu documents/document_chunks.';
  end if;
end
$guard$;

create or replace function public.retire_document(p_doc_id uuid, p_reason text default null)
returns public.documents
language plpgsql
security definer
set search_path = public, extensions
as $$
declare v_row public.documents;
begin
  if not public.user_has_any_role(array['admin'::public.user_role_name,'qa_manager'::public.user_role_name]) then
    raise exception 'retire_document: chỉ admin/qa_manager mới được ngừng sử dụng tài liệu.';
  end if;

  update public.documents
     set status = 'archived'::public.document_status,
         approved_for_ai_use = false,
         reviewed_by = auth.uid(),
         reviewed_at = now(),
         updated_at = now()
   where id = p_doc_id
   returning * into v_row;
  if not found then
    raise exception 'retire_document: không tìm thấy tài liệu %.', p_doc_id;
  end if;

  update public.document_chunks
     set status = 'archived'::public.document_status
   where document_id = p_doc_id and status <> 'archived'::public.document_status;

  update public.document_versions
     set index_status = 'retired', approved_for_ai_use = false
   where document_id = p_doc_id;

  return v_row;
end
$$;

comment on function public.retire_document(uuid, text) is
  'CRAVE-040: ngừng sử dụng (hết hạn) tài liệu — ẩn khỏi retrieval, giữ lineage. Chỉ admin/qa_manager. Reason ghi kèm lời gọi (audit ở lớp app/WF).';

create or replace function public.reactivate_document(p_doc_id uuid)
returns public.documents
language plpgsql
security definer
set search_path = public, extensions
as $$
declare v_row public.documents;
begin
  if not public.user_has_any_role(array['admin'::public.user_role_name,'qa_manager'::public.user_role_name]) then
    raise exception 'reactivate_document: chỉ admin/qa_manager mới được kích hoạt lại.';
  end if;

  update public.documents
     set status = 'approved_for_ai_use'::public.document_status,
         approved_for_ai_use = true,
         reviewed_by = auth.uid(),
         reviewed_at = now(),
         updated_at = now()
   where id = p_doc_id
   returning * into v_row;
  if not found then
    raise exception 'reactivate_document: không tìm thấy tài liệu %.', p_doc_id;
  end if;

  update public.document_chunks
     set status = 'approved_for_ai_use'::public.document_status
   where document_id = p_doc_id and status = 'archived'::public.document_status;

  update public.document_versions
     set index_status = 'ready', approved_for_ai_use = true
   where document_id = p_doc_id;

  return v_row;
end
$$;

comment on function public.reactivate_document(uuid) is
  'CRAVE-040: hoàn tác retire — kích hoạt lại tài liệu (approved_for_ai_use). Chỉ admin/qa_manager.';

revoke all on function public.retire_document(uuid, text) from public, anon;
revoke all on function public.reactivate_document(uuid) from public, anon;
grant execute on function public.retire_document(uuid, text) to authenticated, service_role;
grant execute on function public.reactivate_document(uuid) to authenticated, service_role;

commit;
