begin;
drop trigger if exists ai_query_sources_aa_autofill on public.ai_query_sources;
drop function if exists public.crave_autofill_ai_query_source();
commit;
