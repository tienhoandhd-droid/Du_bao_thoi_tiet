-- CRAVE deploy migration: 20260702160000_047_approve_document
-- Semantic source ID: CRAVE-047 / duyệt tài liệu chính thức (human QA) → vào retrieval gate
-- Project: bdttccztjtrcaztjgkot
--
-- approve_document: admin/qa_manager duyệt tài liệu 'indexed' (pending) → gate-eligible:
--   document_versions: content_sha256 (=binary nếu null), hash_status='verified',
--     approval_evidence_status='verified', index_status='ready'
--     (constraint 027: approval_evidence='verified' cần content_sha256 + hash='verified').
--   documents: status='approved_for_ai_use' + approved_for_ai_use=true + reviewed_by/at.
--   document_chunks: status='approved_for_ai_use'.
-- Fail-closed: chỉ admin/qa; AI KHÔNG tự gọi (đây là human sign-off). Verify: đã test
-- trên PDA-TR-03 → 91 chunk vào gate. Đối xứng với retire_document (042).

begin;

create or replace function public.approve_document(p_doc_id uuid)
returns public.documents
language plpgsql
security definer
set search_path = public, extensions
as $$
declare v_row public.documents; v_ver uuid;
begin
  if not public.user_has_any_role(array['admin'::public.user_role_name,'qa_manager'::public.user_role_name]) then
    raise exception 'approve_document: chỉ admin/qa_manager mới được duyệt tài liệu cho AI.';
  end if;

  select current_version_id into v_ver from public.documents where id = p_doc_id;
  if v_ver is null then
    raise exception 'approve_document: tài liệu % chưa có current_version_id.', p_doc_id;
  end if;

  update public.document_versions
     set content_sha256 = coalesce(content_sha256, binary_sha256),
         hash_status = 'verified',
         approval_evidence_status = 'verified',
         index_status = 'ready'
   where id = v_ver;

  update public.documents
     set status = 'approved_for_ai_use'::public.document_status,
         approved_for_ai_use = true,
         reviewed_by = auth.uid(),
         reviewed_at = now(),
         updated_at = now()
   where id = p_doc_id
   returning * into v_row;
  if not found then raise exception 'approve_document: không tìm thấy tài liệu %.', p_doc_id; end if;

  update public.document_chunks
     set status = 'approved_for_ai_use'::public.document_status
   where document_id = p_doc_id and status = 'indexed'::public.document_status;

  return v_row;
end
$$;

comment on function public.approve_document(uuid) is
  'CRAVE-047: human QA duyệt tài liệu indexed→approved_for_ai_use (version verified + chunks approved) → vào retrieval gate. Chỉ admin/qa_manager.';

revoke all on function public.approve_document(uuid) from public, anon;
grant execute on function public.approve_document(uuid) to authenticated, service_role;

commit;
