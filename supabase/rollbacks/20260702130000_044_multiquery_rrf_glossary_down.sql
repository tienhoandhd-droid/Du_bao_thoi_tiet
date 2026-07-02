begin;
drop function if exists public.hybrid_search_multi_v1(text[], text[], double precision, integer, uuid, text, text, text, integer, text, numeric, integer, integer);
drop table if exists public.gmp_glossary;
commit;
