-- Rollback 031b: gỡ semantic_cache + hàm/trigger liên quan.
begin;
drop trigger if exists semantic_cache_invalidate_trg on public.documents;
drop function if exists public.trg_semantic_cache_on_document_change();
drop function if exists public.semantic_cache_invalidate_for_document(uuid, text);
drop function if exists public.semantic_cache_lookup_v1(extensions.vector, double precision, text);
drop table if exists public.semantic_cache;
commit;
