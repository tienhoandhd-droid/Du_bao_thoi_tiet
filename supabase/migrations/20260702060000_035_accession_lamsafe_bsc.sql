-- CRAVE deploy migration: 20260702060000_035_accession_lamsafe_bsc
-- Accession GĐ2b: promote staging (crave_ingest_lamsafe, 26 chunk đã embed 1536) -> corpus VERIFIED.
-- Tài liệu thật: Hướng dẫn lắp đặt & vận hành Tủ An Toàn Sinh Học cấp II loại A2 (LAMSAFE).
-- Nguồn: Drive controlled của chủ sở hữu (file 1PqmkUQUXLL6N3CgzEv-_xOPGH10n_4cb).
-- Governance: KHÔNG có AI duyệt. approved_by = chủ sở hữu (upload controlled = phê duyệt của con người).
-- Bằng chứng provenance thật (GĐ1): binary/content sha256 tính qua pgcrypto; parse n8n Extract-from-PDF.
-- Idempotent: bỏ qua nếu document_code đã tồn tại.

begin;

do $accession$
declare
  v_doc_id   uuid := gen_random_uuid();
  v_group_id uuid := gen_random_uuid();
  v_ver_id   uuid := gen_random_uuid();
  v_raw_id   uuid := gen_random_uuid();
  v_owner    uuid := '08d0572c-9368-4034-bb26-ab1c88bd9e04';
  v_bsha     text := '9de58a48669e4f00c6b4e284cd435a5000e03e6ee4b7c3c37121a1289ff6a828';
  v_csha     text := 'c6726ca2261b3c654b2e1285d4c2c41c5e7d5bb64709e7a47fa948ae9c60ee18';
  v_n        integer;
begin
  if to_regclass('public.crave_ingest_lamsafe') is null then
    raise exception 'CRAVE-035: thiếu bảng staging crave_ingest_lamsafe (chạy accession S2 embed trước).';
  end if;
  select count(*) into v_n from public.crave_ingest_lamsafe;
  if v_n = 0 then
    raise exception 'CRAVE-035: staging rỗng.';
  end if;
  if exists (select 1 from public.documents where document_code = 'LV-BSC-A2') then
    raise notice 'CRAVE-035: LV-BSC-A2 đã accession, bỏ qua.';
    return;
  end if;
  if not exists (select 1 from public.user_profiles where id = v_owner) then
    raise exception 'CRAVE-035: không tìm thấy user_profile chủ sở hữu %.', v_owner;
  end if;

  -- 1) documents (logical record) — approved theo nguồn controlled của owner
  insert into public.documents (
    id, document_group_id, document_code, document_title, document_type,
    language_code, source_language, source_type, status, approved_for_ai_use,
    file_name, file_hash, mime_type, page_count, chunk_count, gdrive_file_id,
    source_category, trust_level, source_organization, equipment_type,
    validation_type, effective_date, uploaded_by, uploaded_at,
    reviewed_by, reviewed_at, approved_by, approved_at, current_version_id
  ) values (
    v_doc_id, v_group_id, 'LV-BSC-A2',
    'Hướng dẫn lắp đặt và vận hành Tủ An Toàn Sinh Học cấp II loại A2 (LAMSAFE)',
    'manual', 'vi', 'vi', 'equipment_doc', 'approved_for_ai_use', true,
    'Huong-Dan-Lap-Dat-Va-Van-Hanh-Tu-An-Toan-Sinh-Hoc-Cap-Ii-Loai-A2.pdf',
    v_bsha, 'application/pdf', 18, v_n, '1PqmkUQUXLL6N3CgzEv-_xOPGH10n_4cb',
    'internal', 3, 'LAM VIET SCIENTIFIC TECHNOLOGY / LAMSAFE', 'biosafety_cabinet',
    'equipment_qualification', current_date, v_owner, now(),
    v_owner, now(), v_owner, now(), null
  );

  -- 2a) raw_files — bằng chứng file nhị phân gốc (verified, cùng doc + cùng binary sha256)
  insert into public.raw_files (
    id, document_id, drive_file_id, drive_folder_id, file_name, mime_type,
    file_size_bytes, binary_sha256, hash_status, status, storage_provider,
    stored_by, stored_at, verified_at
  ) values (
    v_raw_id, v_doc_id, '1PqmkUQUXLL6N3CgzEv-_xOPGH10n_4cb', '15Fo7BqcDQJqzPPuqds-AuScqeNqOyLUz',
    'Huong-Dan-Lap-Dat-Va-Van-Hanh-Tu-An-Toan-Sinh-Hoc-Cap-Ii-Loai-A2.pdf', 'application/pdf',
    1093396, v_bsha, 'verified', 'verified', 'google_drive',
    v_owner, now(), now()
  );

  -- 2b) document_versions — VERIFIED (hash/parse/approval) + immutable
  insert into public.document_versions (
    id, document_id, version_label, record_origin, raw_file_id, effective_date,
    binary_sha256, content_sha256, hash_status, license_status,
    parse_status, parse_quality_score, parse_engine, parse_engine_version, parsed_at,
    approval_evidence_status, approved_for_ai_use, approved_by, approved_at, index_status
  ) values (
    v_ver_id, v_doc_id, '01', 'ingest', v_raw_id, current_date,
    v_bsha, v_csha, 'verified', 'curated',
    'success', 95, 'n8n-extractFromFile-pdf', '1.1', now(),
    'verified', true, v_owner, now(), 'ready'
  );

  -- 3) trỏ current version
  update public.documents set current_version_id = v_ver_id where id = v_doc_id;

  -- 4) document_chunks từ staging (embedding thật 1536)
  insert into public.document_chunks (
    id, document_id, content, chunk_index, page_number,
    document_code, document_version, document_version_id,
    language_code, source_type, status, embedding,
    trust_level, source_category, source_organization, quality_score, file_hash
  )
  select
    gen_random_uuid(), v_doc_id, s.text,
    (row_number() over (order by s.id))::int - 1, 1,
    'LV-BSC-A2', '01', v_ver_id,
    'vi', 'equipment_doc', 'approved_for_ai_use', s.embedding,
    3, 'internal', 'LAM VIET SCIENTIFIC TECHNOLOGY / LAMSAFE', 0.80, v_csha
  from public.crave_ingest_lamsafe s;

  raise notice 'CRAVE-035: accession LV-BSC-A2 xong — % chunk.', v_n;
end
$accession$;

commit;
