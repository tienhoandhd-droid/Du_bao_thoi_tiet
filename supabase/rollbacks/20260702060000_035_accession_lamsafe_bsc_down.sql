-- CRAVE rollback: 20260702060000_035_accession_lamsafe_bsc_down
-- Gỡ accession LV-BSC-A2. Lưu ý: document_versions có immutability trigger (027) — có thể chặn DELETE;
-- nếu bị chặn cần disable trigger có kiểm soát hoặc xử lý theo change-control.

begin;

do $rb$
declare
  v_doc_id uuid;
begin
  select id into v_doc_id from public.documents where document_code = 'LV-BSC-A2';
  if v_doc_id is null then
    raise notice 'CRAVE-035-down: không có LV-BSC-A2.';
    return;
  end if;
  delete from public.document_chunks where document_id = v_doc_id;
  update public.documents set current_version_id = null where id = v_doc_id;
  delete from public.document_versions where document_id = v_doc_id;
  delete from public.documents where id = v_doc_id;
end
$rb$;

drop table if exists public.crave_ingest_lamsafe;

commit;
