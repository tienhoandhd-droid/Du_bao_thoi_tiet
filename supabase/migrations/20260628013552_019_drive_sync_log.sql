-- CRAVE Chat 16 - Migration 019: nhật ký đồng bộ tệp lên Google Drive.
-- Idempotent: bảng và các policy có thể được tạo lại an toàn.

begin;

create table if not exists public.drive_sync_log (
  id uuid default gen_random_uuid() primary key,
  triggered_by uuid references auth.users(id),
  file_path text not null,
  drive_file_id text,
  status text not null default 'pending',
  error_message text,
  synced_at timestamptz,
  created_at timestamptz default now()
);

alter table public.drive_sync_log enable row level security;

revoke all privileges on table public.drive_sync_log from public, anon, authenticated;
grant select, insert on table public.drive_sync_log to authenticated;

do $policy$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'drive_sync_log'
      and policyname = 'drive_sync_log_select_own'
  ) then
    create policy drive_sync_log_select_own
      on public.drive_sync_log
      for select
      to authenticated
      using (triggered_by = auth.uid());
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'drive_sync_log'
      and policyname = 'drive_sync_log_insert_own'
  ) then
    create policy drive_sync_log_insert_own
      on public.drive_sync_log
      for insert
      to authenticated
      with check (triggered_by = auth.uid());
  end if;
end
$policy$;

commit;
