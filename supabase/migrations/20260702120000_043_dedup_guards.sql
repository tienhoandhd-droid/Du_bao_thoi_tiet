-- CRAVE deploy migration: 20260702120000_043_dedup_guards
-- Semantic source ID: CRAVE-043 / chống trùng tài liệu (logical + content)
-- Project: bdttccztjtrcaztjgkot
--
-- 2 tầng chống trùng + 1 hàm kiểm tra trước khi nạp:
--   (1) documents.document_code DUY NHẤT (trùng mã logic → chặn).
--   (2) raw_files.binary_sha256 DUY NHẤT (trùng nội dung nhị phân → chặn),
--       bổ sung cho unique(drive_file_id) đã có (trùng file Drive).
--   (3) find_document_by_hash(sha): trả document_code đã tồn tại cho 1 hash —
--       gate/ingest gọi TRƯỚC khi tải/scan/accession để bỏ qua tài liệu đã có.
-- Data hiện tại: 27/27 mã distinct, 0 hash trùng → thêm unique an toàn.

begin;

do $guard$
begin
  if exists (select 1 from (select document_code from public.documents group by document_code having count(*)>1) x) then
    raise exception 'CRAVE-043: đang có document_code trùng — xử lý trước khi thêm unique.';
  end if;
  if exists (select 1 from (select binary_sha256 from public.raw_files where binary_sha256 is not null group by binary_sha256 having count(*)>1) y) then
    raise exception 'CRAVE-043: đang có binary_sha256 trùng — xử lý trước.';
  end if;
end
$guard$;

create unique index if not exists uq_documents_document_code
  on public.documents (document_code);

create unique index if not exists uq_raw_files_binary_sha256
  on public.raw_files (binary_sha256)
  where binary_sha256 is not null;

create or replace function public.find_document_by_hash(p_sha text)
returns table(document_code text, matched_in text)
language sql stable security definer set search_path = public, extensions
as $$
  select d.document_code, 'raw_files'::text
  from public.raw_files r join public.documents d on d.id = r.document_id
  where r.binary_sha256 = p_sha
  union
  select d.document_code, 'document_versions'::text
  from public.document_versions v join public.documents d on d.id = v.document_id
  where v.binary_sha256 = p_sha or v.content_sha256 = p_sha;
$$;

comment on function public.find_document_by_hash(text) is
  'CRAVE-043: trả document_code đã tồn tại cho 1 sha256 (binary/content). Ingest gọi trước khi tải/scan để chống trùng.';

revoke all on function public.find_document_by_hash(text) from public, anon;
grant execute on function public.find_document_by_hash(text) to authenticated, service_role;

commit;
