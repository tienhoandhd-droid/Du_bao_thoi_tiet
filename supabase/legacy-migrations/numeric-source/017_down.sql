-- CRAVE Chat 14 - Rollback Migration 017.

begin;

drop table if exists public.glossary;

alter table if exists public.documents
  drop column if exists equipment_code;

commit;
