-- CRAVE deploy migration: 20260629191000_027_immutable_document_versions
-- Semantic source ID: CRAVE-027 / R04-A01 / UPG-CHAT-05
-- Project: bdttccztjtrcaztjgkot
-- KHÔNG tự apply; cần exact dry-run/change set/approval riêng.

begin;

do $preflight$
begin
  if to_regclass('public.documents') is null
    or to_regclass('public.raw_files') is null
    or to_regclass('public.source_registry') is null
    or to_regclass('public.user_profiles') is null
  then
    raise exception 'CRAVE-027: thiếu documents/raw_files/source_registry/user_profiles.';
  end if;

  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-027: thiếu user_has_any_role(user_role_name[]).';
  end if;

  if to_regclass('public.document_versions') is not null
    and coalesce(obj_description(to_regclass('public.document_versions'), 'pg_class'), '')
      not like 'CRAVE-027:%'
  then
    raise exception 'CRAVE-027: document_versions hiện có không mang marker CRAVE-027.';
  end if;

  if exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='documents'
      and column_name='current_version_id'
  ) and to_regclass('public.document_versions') is null then
    raise exception 'CRAVE-027: current_version_id tồn tại nhưng document_versions không tồn tại.';
  end if;

  if to_regprocedure('public.crave_enforce_document_version_immutability()') is not null
    and coalesce(
      obj_description(
        to_regprocedure('public.crave_enforce_document_version_immutability()'),
        'pg_proc'
      ),
      ''
    ) not like 'CRAVE-027:%'
  then
    raise exception 'CRAVE-027: immutability function hiện có không mang marker CRAVE-027.';
  end if;

  if to_regprocedure('public.crave_validate_current_document_version()') is not null
    and coalesce(
      obj_description(
        to_regprocedure('public.crave_validate_current_document_version()'),
        'pg_proc'
      ),
      ''
    ) not like 'CRAVE-027:%'
  then
    raise exception 'CRAVE-027: current-version function hiện có không mang marker CRAVE-027.';
  end if;
end
$preflight$;

create table if not exists public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id),
  raw_file_id uuid references public.raw_files(id),
  source_registry_id uuid references public.source_registry(id),
  version_label text not null,
  record_origin text not null default 'ingest'
    check (record_origin in ('ingest','legacy_backfill_027')),
  source_document_id text,
  source_url text,
  source_updated_at timestamptz,
  effective_date date,
  retired_at timestamptz,
  superseded_by_version_id uuid references public.document_versions(id),
  drive_file_id text,
  binary_sha256 text,
  content_sha256 text,
  hash_status text not null default 'pending'
    check (hash_status in ('pending','verified','legacy_missing','mismatch')),
  license_status text not null default 'unknown'
    check (license_status in ('allowed','curated','metadata_only','denied','unknown')),
  parse_status text not null default 'pending'
    check (parse_status in ('pending','running','success','partial','failed','needs_review')),
  parse_quality_score numeric(5,2)
    check (parse_quality_score is null or parse_quality_score between 0 and 100),
  parse_engine text,
  parse_engine_version text,
  parsed_at timestamptz,
  parse_reviewed_by uuid references public.user_profiles(id),
  parse_reviewed_at timestamptz,
  approval_evidence_status text not null default 'missing'
    check (approval_evidence_status in ('missing','verified','revoked')),
  approved_for_ai_use boolean not null default false,
  approved_by uuid references public.user_profiles(id),
  approved_at timestamptz,
  index_status text not null default 'not_ready'
    check (index_status in ('not_ready','queued','indexing','ready','failed','excluded')),
  index_version text,
  created_at timestamptz not null default now(),
  constraint document_versions_doc_label_key unique (document_id, version_label),
  constraint document_versions_version_label_check check (
    length(btrim(version_label)) between 1 and 100
  ),
  constraint document_versions_binary_sha_check check (
    binary_sha256 is null or binary_sha256 ~ '^[0-9a-f]{64}$'
  ),
  constraint document_versions_content_sha_check check (
    content_sha256 is null or content_sha256 ~ '^[0-9a-f]{64}$'
  ),
  constraint document_versions_verified_hash_check check (
    hash_status <> 'verified' or binary_sha256 is not null
  ),
  constraint document_versions_not_self_superseded check (
    superseded_by_version_id is null or superseded_by_version_id <> id
  ),
  constraint document_versions_ai_approval_check check (
    not approved_for_ai_use
    or (
      approval_evidence_status = 'verified'
      and approved_by is not null
      and approved_at is not null
      and binary_sha256 is not null
      and content_sha256 is not null
      and hash_status = 'verified'
      and license_status in ('allowed','curated')
      and parse_status in ('success','partial')
      and parse_quality_score is not null
      and parsed_at is not null
    )
  ),
  constraint document_versions_legacy_fail_closed_check check (
    record_origin <> 'legacy_backfill_027'
    or (
      raw_file_id is null
      and binary_sha256 is null
      and content_sha256 is null
      and hash_status = 'legacy_missing'
      and approval_evidence_status = 'missing'
      and not approved_for_ai_use
      and parse_status = 'needs_review'
      and index_status = 'not_ready'
    )
  )
);

comment on table public.document_versions is
  'CRAVE-027: immutable document-version provenance; legacy backfill fail-closed, không suy diễn document-level approval thành version approval.';

create index if not exists idx_document_versions_document_created
  on public.document_versions (document_id, created_at desc);
create index if not exists idx_document_versions_raw_file
  on public.document_versions (raw_file_id)
  where raw_file_id is not null;
create index if not exists idx_document_versions_content_sha256
  on public.document_versions (content_sha256)
  where content_sha256 is not null;
create index if not exists idx_document_versions_lifecycle
  on public.document_versions (approved_for_ai_use, index_status, retired_at);

alter table public.documents
  add column if not exists current_version_id uuid;

do $current_fk$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid='public.documents'::regclass
      and conname='documents_current_version_id_fkey'
  ) then
    alter table public.documents
      add constraint documents_current_version_id_fkey
      foreign key (current_version_id) references public.document_versions(id);
  end if;
end
$current_fk$;

create or replace function public.crave_enforce_document_version_immutability()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $function$
declare
  linked_document_id uuid;
  linked_status text;
  linked_hash_status text;
  linked_binary_sha256 text;
  superseding_document_id uuid;
begin
  if tg_op = 'DELETE' then
    raise exception 'CRAVE-027: document_versions là evidence bất biến; DELETE bị chặn.';
  end if;

  if tg_op = 'INSERT' and new.record_origin = 'ingest' then
    if new.raw_file_id is null then
      raise exception 'CRAVE-027: ingest version bắt buộc có raw_file_id.';
    end if;

    select document_id, status, hash_status, binary_sha256
    into linked_document_id, linked_status, linked_hash_status, linked_binary_sha256
    from public.raw_files
    where id = new.raw_file_id;

    if not found
      or linked_status <> 'verified'
      or linked_hash_status <> 'verified'
      or linked_binary_sha256 is null
      or new.binary_sha256 is distinct from linked_binary_sha256
      or (linked_document_id is not null and linked_document_id <> new.document_id)
    then
      raise exception 'CRAVE-027: ingest version yêu cầu raw file verified, cùng document và cùng binary SHA-256.';
    end if;
  end if;

  if tg_op = 'UPDATE' then
    if row(
      new.id, new.document_id, new.version_label, new.record_origin,
      new.raw_file_id, new.source_registry_id, new.source_document_id,
      new.source_url, new.source_updated_at, new.effective_date,
      new.drive_file_id, new.binary_sha256, new.created_at
    ) is distinct from row(
      old.id, old.document_id, old.version_label, old.record_origin,
      old.raw_file_id, old.source_registry_id, old.source_document_id,
      old.source_url, old.source_updated_at, old.effective_date,
      old.drive_file_id, old.binary_sha256, old.created_at
    ) then
      raise exception 'CRAVE-027: identity/source/binary provenance của version không được sửa; hãy tạo version mới.';
    end if;

    if old.approved_for_ai_use and row(
      new.content_sha256, new.hash_status, new.license_status,
      new.parse_status, new.parse_quality_score, new.parse_engine,
      new.parse_engine_version, new.parsed_at, new.parse_reviewed_by,
      new.parse_reviewed_at, new.approval_evidence_status,
      new.approved_for_ai_use, new.approved_by, new.approved_at
    ) is distinct from row(
      old.content_sha256, old.hash_status, old.license_status,
      old.parse_status, old.parse_quality_score, old.parse_engine,
      old.parse_engine_version, old.parsed_at, old.parse_reviewed_by,
      old.parse_reviewed_at, old.approval_evidence_status,
      old.approved_for_ai_use, old.approved_by, old.approved_at
    ) then
      raise exception 'CRAVE-027: approved version bất biến; chỉ được retire/supersede hoặc cập nhật index lifecycle.';
    end if;

    if new.superseded_by_version_id is distinct from old.superseded_by_version_id
      and new.superseded_by_version_id is not null
    then
      select document_id into superseding_document_id
      from public.document_versions
      where id=new.superseded_by_version_id;

      if not found or superseding_document_id <> old.document_id then
        raise exception 'CRAVE-027: superseding version phải thuộc cùng logical document.';
      end if;

      if exists (
        select 1 from public.documents d
        where d.id=old.document_id and d.current_version_id=old.id
      ) then
        raise exception 'CRAVE-027: phải chuyển current_version_id sang version mới trước khi supersede version cũ.';
      end if;
    end if;
  end if;

  return new;
end
$function$;

comment on function public.crave_enforce_document_version_immutability() is
  'CRAVE-027: chặn DELETE, chặn sửa identity/source/binary provenance và khóa parse/approval evidence sau approval.';

create or replace function public.crave_validate_current_document_version()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $function$
declare
  version_document_id uuid;
  version_superseded_by uuid;
begin
  if new.current_version_id is null then
    return new;
  end if;

  select document_id, superseded_by_version_id
  into version_document_id, version_superseded_by
  from public.document_versions
  where id = new.current_version_id;

  if not found or version_document_id <> new.id then
    raise exception 'CRAVE-027: current_version_id phải thuộc cùng logical document.';
  end if;

  if version_superseded_by is not null then
    raise exception 'CRAVE-027: current_version_id không được trỏ version đã superseded.';
  end if;

  return new;
end
$function$;

comment on function public.crave_validate_current_document_version() is
  'CRAVE-027: current pointer phải trỏ version cùng logical document và chưa superseded.';

do $triggers$
begin
  if not exists (
    select 1 from pg_trigger
    where tgrelid='public.document_versions'::regclass
      and tgname='document_versions_enforce_immutability' and not tgisinternal
  ) then
    create trigger document_versions_enforce_immutability
      before insert or update or delete on public.document_versions
      for each row execute function public.crave_enforce_document_version_immutability();
  end if;

  if not exists (
    select 1 from pg_trigger
    where tgrelid='public.documents'::regclass
      and tgname='documents_validate_current_version' and not tgisinternal
  ) then
    create trigger documents_validate_current_version
      before insert or update of current_version_id on public.documents
      for each row execute function public.crave_validate_current_document_version();
  end if;
end
$triggers$;

insert into public.document_versions (
  document_id,
  version_label,
  record_origin,
  source_url,
  effective_date,
  drive_file_id,
  hash_status,
  license_status,
  parse_status,
  approval_evidence_status,
  approved_for_ai_use,
  index_status,
  created_at
)
select
  d.id,
  coalesce(nullif(btrim(d.version), ''), 'legacy'),
  'legacy_backfill_027',
  d.source_url,
  d.effective_date,
  d.gdrive_file_id,
  'legacy_missing',
  'unknown',
  'needs_review',
  'missing',
  false,
  'not_ready',
  d.created_at
from public.documents d
on conflict (document_id, version_label) do nothing;

update public.documents d
set current_version_id = v.id
from public.document_versions v
where v.document_id = d.id
  and v.record_origin = 'legacy_backfill_027'
  and d.current_version_id is null;

do $reconcile$
declare
  missing_legacy bigint;
  bad_pointer bigint;
  false_evidence bigint;
begin
  select count(*) into missing_legacy
  from public.documents d
  where (
    select count(*)
    from public.document_versions v
    where v.document_id=d.id and v.record_origin='legacy_backfill_027'
  ) <> 1;

  select count(*) into bad_pointer
  from public.documents d
  left join public.document_versions v on v.id=d.current_version_id
  where d.current_version_id is null or v.document_id is distinct from d.id;

  select count(*) into false_evidence
  from public.document_versions v
  where v.record_origin='legacy_backfill_027'
    and (
      v.raw_file_id is not null
      or v.binary_sha256 is not null
      or v.content_sha256 is not null
      or v.hash_status <> 'legacy_missing'
      or v.approval_evidence_status <> 'missing'
      or v.approved_for_ai_use
      or v.parse_status <> 'needs_review'
      or v.index_status <> 'not_ready'
    );

  if missing_legacy <> 0 or bad_pointer <> 0 or false_evidence <> 0 then
    raise exception 'CRAVE-027: reconciliation fail missing=% bad_pointer=% false_evidence=%.',
      missing_legacy, bad_pointer, false_evidence;
  end if;
end
$reconcile$;

alter table public.document_versions enable row level security;

do $policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='document_versions'
      and policyname='document_versions_select_authorized'
  ) then
    create policy document_versions_select_authorized on public.document_versions
      for select to authenticated
      using (
        exists (
          select 1 from public.documents d
          where d.id=document_versions.document_id
        )
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='document_versions'
      and policyname='document_versions_insert_governance'
  ) then
    create policy document_versions_insert_governance on public.document_versions
      for insert to authenticated
      with check (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]));
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='document_versions'
      and policyname='document_versions_update_governance'
  ) then
    create policy document_versions_update_governance on public.document_versions
      for update to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]))
      with check (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]));
  end if;
end
$policies$;

revoke all on public.document_versions from public, anon;
grant select, insert, update on public.document_versions to authenticated;

revoke all on function public.crave_enforce_document_version_immutability()
  from public, anon, authenticated, service_role;
revoke all on function public.crave_validate_current_document_version()
  from public, anon, authenticated, service_role;

commit;
