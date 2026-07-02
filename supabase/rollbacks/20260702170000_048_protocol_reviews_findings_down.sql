begin;
alter table public.protocol_reviews drop column if exists findings;
commit;
