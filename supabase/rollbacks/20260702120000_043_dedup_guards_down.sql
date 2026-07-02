begin;
drop function if exists public.find_document_by_hash(text);
drop index if exists public.uq_raw_files_binary_sha256;
drop index if exists public.uq_documents_document_code;
commit;
