-- CRAVE Chat 14 - Migration 017: equipment-aware documents and glossary.
-- Idempotent: the column, table, policies, index and language correction are safe to rerun.

begin;

do $migration$
begin
  if not exists (
    select 1
    from pg_attribute a
    join pg_class c on c.oid = a.attrelid
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'documents'
      and c.relkind in ('r', 'p')
      and a.attname = 'equipment_code'
      and not a.attisdropped
  ) then
    alter table public.documents
      add column equipment_code text;
  end if;
end
$migration$;

do $migration$
begin
  if not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'glossary'
      and c.relkind in ('r', 'p')
  ) then
    create table public.glossary (
      id uuid primary key default gen_random_uuid(),
      term text not null unique,
      definition text not null,
      category text,
      source_doc_code text,
      language_code text default 'vi',
      created_at timestamptz default now()
    );
  end if;
end
$migration$;

-- Correct documents that were classified as Vietnamese-only even though their
-- metadata or their linked chunks show that they contain both VI and EN.
update public.documents as d
set language_code = 'vi-en'
where d.language_code = 'vi'
  and (
    lower(coalesce(d.document_title, '')) like '%bilingual%'
    or lower(coalesce(d.source_category, '')) like '%bilingual%'
    or (
      exists (
        select 1
        from public.document_chunks as dc_vi
        where dc_vi.document_id = d.id
          and dc_vi.language_code = 'vi'
      )
      and exists (
        select 1
        from public.document_chunks as dc_en
        where dc_en.document_id = d.id
          and dc_en.language_code = 'en'
      )
    )
  );

alter table public.glossary enable row level security;

revoke all privileges on table public.glossary from public, anon, authenticated;
grant select on table public.glossary to authenticated;
grant select, insert, update, delete on table public.glossary to service_role;

do $policy$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'glossary'
      and policyname = 'glossary_select_authenticated'
  ) then
    create policy glossary_select_authenticated
      on public.glossary
      for select
      to authenticated
      using (true);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'glossary'
      and policyname = 'glossary_insert_service_role'
  ) then
    create policy glossary_insert_service_role
      on public.glossary
      for insert
      to service_role
      with check (true);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'glossary'
      and policyname = 'glossary_update_service_role'
  ) then
    create policy glossary_update_service_role
      on public.glossary
      for update
      to service_role
      using (true)
      with check (true);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'glossary'
      and policyname = 'glossary_delete_service_role'
  ) then
    create policy glossary_delete_service_role
      on public.glossary
      for delete
      to service_role
      using (true);
  end if;
end
$policy$;

create index if not exists idx_glossary_term
  on public.glossary (term);

commit;
