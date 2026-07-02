begin;
drop policy if exists doc_figures_read_auth on storage.objects;
delete from storage.buckets where id='doc-figures';
drop table if exists public.document_tables;
drop table if exists public.document_figures;
commit;
