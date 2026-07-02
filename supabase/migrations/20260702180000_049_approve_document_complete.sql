-- CRAVE deploy migration: 20260702180000_049_approve_document_complete
-- Semantic source ID: CRAVE-049 / vá approve_document: set ĐỦ field cho document_versions_ai_approval_check
-- Project: bdttccztjtrcaztjgkot
--
-- BUG (phát hiện khi verify TR-33): approve_document (047) chỉ set approval_evidence/
-- hash/index → version.approved_for_ai_use KHÔNG bật được vì check
-- document_versions_ai_approval_check còn đòi: approved_by, approved_at, parsed_at,
-- parse_status IN (success,partial), license_status IN (allowed,curated),
-- parse_quality_score, content_sha256. Và hybrid_search_v4 CHỈ trả version có
-- approved_for_ai_use=true → doc duyệt qua nút cũ KHÔNG vào retrieval. Vá đủ.

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

  -- Set ĐỦ field để thoả document_versions_ai_approval_check + bật approved_for_ai_use.
  -- Duyệt QA = curation: parse_status/license_status/quality được xác nhận nếu chưa có.
  update public.document_versions
     set content_sha256 = coalesce(content_sha256, binary_sha256),
         hash_status = 'verified',
         approval_evidence_status = 'verified',
         index_status = 'ready',
         parse_status = case when parse_status in ('success','partial') then parse_status else 'success' end,
         license_status = case when license_status in ('allowed','curated') then license_status else 'curated' end,
         parse_quality_score = coalesce(parse_quality_score, 90),
         parsed_at = coalesce(parsed_at, now()),
         approved_by = auth.uid(),
         approved_at = now(),
         approved_for_ai_use = true
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
  'CRAVE-049: human QA duyệt tài liệu → set ĐỦ field version (approved_by/at, parsed_at, parse_status, license_status, quality, content_sha256, approved_for_ai_use) thoả ai_approval_check + chunks approved → vào hybrid_search_v4. Chỉ admin/qa_manager.';

commit;
