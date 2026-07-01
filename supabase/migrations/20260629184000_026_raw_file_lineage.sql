-- CRAVE deploy migration: 20260629184000_026_raw_file_lineage
-- Semantic source ID: CRAVE-026 / R03-A01 / UPG-CHAT-04
-- Project: bdttccztjtrcaztjgkot
-- KHÔNG tự apply; cần exact dry-run/change set/approval riêng.

begin;

do $preflight$
begin
  if to_regclass('public.source_registry') is null then
    raise exception 'CRAVE-026: thiếu source_registry; migration 025 phải chạy trước.';
  end if;
  if to_regclass('public.gdrive_sources') is null
    or to_regclass('public.drive_sync_log') is null
    or to_regclass('public.documents') is null
  then
    raise exception 'CRAVE-026: thiếu bảng legacy bắt buộc.';
  end if;
  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null
    or to_regprocedure('public.update_updated_at()') is null
  then
    raise exception 'CRAVE-026: thiếu role/update helper.';
  end if;
  if to_regclass('public.raw_files') is not null
    and coalesce(obj_description(to_regclass('public.raw_files'), 'pg_class'), '')
      not like 'CRAVE-026:%'
  then
    raise exception 'CRAVE-026: raw_files hiện có không mang marker CRAVE-026.';
  end if;
end
$preflight$;

create table if not exists public.raw_files (
  id uuid primary key default gen_random_uuid(),
  source_registry_id uuid references public.source_registry(id),
  document_id uuid references public.documents(id),
  drive_file_id text not null,
  drive_folder_id text,
  file_name text not null,
  mime_type text not null,
  file_size_bytes bigint check (file_size_bytes is null or file_size_bytes >= 0),
  binary_sha256 text,
  hash_status text not null default 'pending'
    check (hash_status in ('pending','verified','legacy_missing','mismatch')),
  status text not null default 'stored'
    check (status in ('stored','verified','legacy_unverified','rejected','quarantined','failed')),
  storage_provider text not null default 'google_drive'
    check (storage_provider in ('google_drive','controlled_upload')),
  storage_path_hint text,
  stored_by uuid references auth.users(id),
  stored_at timestamptz not null default now(),
  verified_at timestamptz,
  legacy_gdrive_source_ids uuid[] not null default '{}',
  legacy_drive_sync_log_ids uuid[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint raw_files_drive_file_key unique (drive_file_id),
  constraint raw_files_drive_id_check check (length(btrim(drive_file_id)) between 1 and 512),
  constraint raw_files_file_name_check check (length(btrim(file_name)) between 1 and 500),
  constraint raw_files_mime_type_check check (length(btrim(mime_type)) between 1 and 255),
  constraint raw_files_sha256_check check (
    binary_sha256 is null or binary_sha256 ~ '^[0-9a-f]{64}$'
  ),
  constraint raw_files_verified_check check (
    status <> 'verified'
    or (
      hash_status = 'verified'
      and binary_sha256 is not null
      and verified_at is not null
    )
  ),
  constraint raw_files_hash_state_check check (
    hash_status <> 'verified' or binary_sha256 is not null
  )
);

comment on table public.raw_files is
  'CRAVE-026: raw-file metadata/Drive/hash lineage; DB không lưu binary; legacy sync không được coi là hash verified.';

create index if not exists idx_raw_files_hash_status
  on public.raw_files (hash_status, status);
create index if not exists idx_raw_files_binary_sha256
  on public.raw_files (binary_sha256)
  where binary_sha256 is not null;
create index if not exists idx_raw_files_document
  on public.raw_files (document_id)
  where document_id is not null;

-- gdrive_sources hiện rỗng trên baseline, nhưng mapping giữ idempotent cho drift.
insert into public.raw_files (
  document_id, drive_file_id, drive_folder_id, file_name, mime_type,
  hash_status, status, storage_provider, stored_by, stored_at,
  legacy_gdrive_source_ids
)
select
  g.document_id,
  g.gdrive_file_id,
  g.gdrive_folder_id,
  g.file_name,
  coalesce(nullif(btrim(g.mime_type), ''), 'application/octet-stream'),
  'legacy_missing',
  'legacy_unverified',
  'google_drive',
  g.added_by,
  coalesce(g.last_synced_at, g.created_at, now()),
  array[g.id]
from public.gdrive_sources g
on conflict (drive_file_id) do update
set legacy_gdrive_source_ids = (
      select array_agg(distinct value order by value)
      from unnest(raw_files.legacy_gdrive_source_ids || excluded.legacy_gdrive_source_ids)
        as valueset(value)
    ),
    document_id = coalesce(raw_files.document_id, excluded.document_id),
    drive_folder_id = coalesce(raw_files.drive_folder_id, excluded.drive_folder_id);

-- drive_sync_log.synced chỉ chứng minh upload từng thành công, không có binary hash.
with legacy as (
  select
    l.drive_file_id,
    min(regexp_replace(l.file_path, '^.*/', '')) as file_name,
    min(l.file_path) as storage_path_hint,
    min(l.triggered_by::text)::uuid as stored_by,
    min(coalesce(l.synced_at, l.created_at, now())) as stored_at,
    array_agg(distinct l.id order by l.id) as legacy_ids
  from public.drive_sync_log l
  where nullif(btrim(l.drive_file_id), '') is not null
  group by l.drive_file_id
)
insert into public.raw_files (
  drive_file_id, file_name, mime_type, hash_status, status, storage_provider,
  storage_path_hint, stored_by, stored_at, legacy_drive_sync_log_ids
)
select
  drive_file_id,
  coalesce(nullif(btrim(file_name), ''), 'legacy-drive-file'),
  'application/octet-stream',
  'legacy_missing',
  'legacy_unverified',
  'google_drive',
  storage_path_hint,
  stored_by,
  stored_at,
  legacy_ids
from legacy
on conflict (drive_file_id) do update
set legacy_drive_sync_log_ids = (
      select array_agg(distinct value order by value)
      from unnest(raw_files.legacy_drive_sync_log_ids || excluded.legacy_drive_sync_log_ids)
        as valueset(value)
    ),
    storage_path_hint = coalesce(raw_files.storage_path_hint, excluded.storage_path_hint),
    stored_by = coalesce(raw_files.stored_by, excluded.stored_by);

do $reconcile$
declare
  missing_gdrive bigint;
  missing_sync bigint;
begin
  select count(*) into missing_gdrive
  from public.gdrive_sources g
  where not exists (
    select 1 from public.raw_files r where g.id = any(r.legacy_gdrive_source_ids)
  );

  select count(*) into missing_sync
  from public.drive_sync_log l
  where nullif(btrim(l.drive_file_id), '') is not null
    and not exists (
      select 1 from public.raw_files r where l.id = any(r.legacy_drive_sync_log_ids)
    );

  if missing_gdrive > 0 or missing_sync > 0 then
    raise exception 'CRAVE-026: legacy reconciliation thiếu gdrive=% drive_sync=%.',
      missing_gdrive, missing_sync;
  end if;
end
$reconcile$;

alter table public.raw_files enable row level security;

do $policies$
begin
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='raw_files'
      and policyname='raw_files_select_authorized'
  ) then
    create policy raw_files_select_authorized on public.raw_files
      for select to authenticated
      using (
        stored_by = auth.uid()
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;

  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='raw_files'
      and policyname='raw_files_insert_authorized'
  ) then
    create policy raw_files_insert_authorized on public.raw_files
      for insert to authenticated
      with check (
        stored_by = auth.uid()
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name
        ])
      );
  end if;

  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='raw_files'
      and policyname='raw_files_update_governance'
  ) then
    create policy raw_files_update_governance on public.raw_files
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

do $trigger$
begin
  if not exists (
    select 1 from pg_trigger where tgrelid='public.raw_files'::regclass
      and tgname='raw_files_set_updated_at' and not tgisinternal
  ) then
    create trigger raw_files_set_updated_at
      before update on public.raw_files
      for each row execute function public.update_updated_at();
  end if;
end
$trigger$;

revoke all on public.raw_files from public, anon;
grant select, insert, update on public.raw_files to authenticated;

commit;
