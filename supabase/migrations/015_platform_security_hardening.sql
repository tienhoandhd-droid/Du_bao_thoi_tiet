-- CRAVE Platform Alignment - Migration 015
-- Mục tiêu:
--   1. Buộc các view tài liệu tuân thủ RLS của người gọi.
--   2. Thu hồi quyền gọi RPC SECURITY DEFINER nguy hiểm từ API public.
--   3. Khóa search_path cho các hàm nền tảng.
--   4. Cưỡng chế audit_log và chat_memory chỉ được ghi nối tiếp.
--
-- CHƯA ĐƯỢC APPLY nếu chưa có xác nhận của người dùng.

begin;

-- Dừng sớm nếu migration chạy nhầm schema/project.
do $$
declare
  required_relation text;
  required_function text;
begin
  foreach required_relation in array array[
    'public.audit_log',
    'public.chat_memory',
    'public.documents',
    'public.documents_effective',
    'public.documents_due_for_review',
    'public.documents_review_soon'
  ]
  loop
    if to_regclass(required_relation) is null then
      raise exception 'CRAVE-015: thiếu relation bắt buộc %; dừng để tránh chạy sai schema.',
        required_relation;
    end if;
  end loop;

  foreach required_function in array array[
    'update_document_status',
    'supersede_document',
    'write_audit_log',
    'get_recent_audit_logs',
    'check_document_duplicate',
    'get_dashboard_stats',
    'get_governance_stats',
    'get_source_stats',
    'hybrid_search',
    'hybrid_search_v2',
    'hybrid_search_v3'
  ]
  loop
    if not exists (
      select 1
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public'
        and p.proname = required_function
    ) then
      raise exception 'CRAVE-015: thiếu function public.%; dừng để tránh migration nửa vời.',
        required_function;
    end if;
  end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- 1. View phải chạy theo quyền người gọi để RLS của bảng documents có hiệu lực.
-- ---------------------------------------------------------------------------
alter view public.documents_effective
  set (security_invoker = true);

alter view public.documents_due_for_review
  set (security_invoker = true);

alter view public.documents_review_soon
  set (security_invoker = true);

revoke all privileges on table public.documents_effective from anon;
revoke all privileges on table public.documents_due_for_review from anon;
revoke all privileges on table public.documents_review_soon from anon;

grant select on table public.documents_effective to authenticated, service_role;
grant select on table public.documents_due_for_review to authenticated, service_role;
grant select on table public.documents_review_soon to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 2. RPC SECURITY DEFINER nguy hiểm chỉ dành cho backend tin cậy.
-- n8n dùng kết nối Postgres GMP-check; frontend không được gọi trực tiếp các RPC.
-- ---------------------------------------------------------------------------
do $$
declare
  function_record record;
  function_signature text;
begin
  for function_record in
    select
      n.nspname,
      p.proname,
      pg_get_function_identity_arguments(p.oid) as identity_arguments
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = any (array[
        'update_document_status',
        'supersede_document',
        'write_audit_log',
        'get_recent_audit_logs',
        'check_document_duplicate',
        'get_dashboard_stats',
        'get_governance_stats',
        'get_source_stats',
        'hybrid_search',
        'hybrid_search_v2',
        'hybrid_search_v3'
      ])
  loop
    function_signature := format(
      '%I.%I(%s)',
      function_record.nspname,
      function_record.proname,
      function_record.identity_arguments
    );

    execute format(
      'revoke all privileges on function %s from public, anon, authenticated',
      function_signature
    );

    execute format(
      'grant execute on function %s to service_role',
      function_signature
    );
  end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- 3. Khóa search_path để tránh object shadowing trong function.
-- Giữ user_has_role/user_has_any_role callable vì RLS đang phụ thuộc hai hàm này.
-- ---------------------------------------------------------------------------
do $$
declare
  function_record record;
  function_signature text;
begin
  for function_record in
    select
      n.nspname,
      p.proname,
      pg_get_function_identity_arguments(p.oid) as identity_arguments
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = any (array[
        'user_has_role',
        'user_has_any_role',
        'write_audit_log',
        'hybrid_search',
        'check_document_duplicate',
        'get_dashboard_stats',
        'get_recent_audit_logs',
        'update_document_status',
        'update_updated_at',
        'hybrid_search_v2',
        'get_source_stats',
        'document_is_currently_valid',
        'get_lifecycle_state',
        'supersede_document',
        'compute_chunk_quality',
        'hybrid_search_v3',
        'get_governance_stats'
      ])
  loop
    function_signature := format(
      '%I.%I(%s)',
      function_record.nspname,
      function_record.proname,
      function_record.identity_arguments
    );

    execute format(
      'alter function %s set search_path to pg_catalog, public, extensions',
      function_signature
    );
  end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- 4. Trigger chung chặn UPDATE/DELETE/TRUNCATE trên bảng append-only.
-- Trigger statement-level vẫn chặn được credential Postgres bypass RLS.
-- ---------------------------------------------------------------------------
create or replace function public.crave_block_append_only_mutation()
returns trigger
language plpgsql
set search_path to pg_catalog, public
as $$
begin
  raise exception using
    errcode = '55000',
    message = format(
      'CRAVE append-only guard: không cho phép % trên %.%',
      tg_op,
      tg_table_schema,
      tg_table_name
    );
end;
$$;

comment on function public.crave_block_append_only_mutation() is
  'CRAVE-015: chặn UPDATE, DELETE và TRUNCATE trên bảng append-only.';

do $$
begin
  if not exists (
    select 1
    from pg_trigger
    where tgrelid = 'public.audit_log'::regclass
      and tgname = 'audit_log_append_only_guard'
      and not tgisinternal
  ) then
    create trigger audit_log_append_only_guard
      before update or delete or truncate on public.audit_log
      for each statement
      execute function public.crave_block_append_only_mutation();
  end if;

  if not exists (
    select 1
    from pg_trigger
    where tgrelid = 'public.chat_memory'::regclass
      and tgname = 'chat_memory_append_only_guard'
      and not tgisinternal
  ) then
    create trigger chat_memory_append_only_guard
      before update or delete or truncate on public.chat_memory
      for each statement
      execute function public.crave_block_append_only_mutation();
  end if;
end
$$;

-- ---------------------------------------------------------------------------
-- 5. Audit chỉ được đọc bởi người đã xác thực có policy phù hợp và chỉ backend
-- tin cậy được INSERT. Bỏ policy public WITH CHECK (true).
-- Lưu ý: view_audit_log (SELECT, roles {public}) được chuyển sang {authenticated}
-- để khớp với grant ở dưới và tránh nhầm lẫn scope.
-- ---------------------------------------------------------------------------
alter table public.audit_log enable row level security;

drop policy if exists insert_audit_log on public.audit_log;

-- Cập nhật scope view_audit_log từ {public} sang {authenticated} cho rõ ràng.
-- Policy này vẫn yêu cầu user_has_any_role(admin/qa_manager/auditor) nên không mở rộng quyền.
do $$
begin
  if exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='audit_log' and policyname='view_audit_log'
  ) then
    drop policy view_audit_log on public.audit_log;
    create policy view_audit_log
      on public.audit_log
      for select
      to authenticated
      using (user_has_any_role(array['admin'::user_role_name, 'qa_manager'::user_role_name, 'auditor'::user_role_name]));
  end if;
end
$$;

revoke all privileges on table public.audit_log from public, anon, authenticated;
revoke update, delete, truncate on table public.audit_log from service_role;

grant select on table public.audit_log to authenticated;
grant select, insert on table public.audit_log to service_role;

-- ---------------------------------------------------------------------------
-- 6. Chat memory giữ SELECT/INSERT; cấm sửa/xóa và thêm index đúng access path.
-- ---------------------------------------------------------------------------
alter table public.chat_memory enable row level security;

revoke all privileges on table public.chat_memory from public, anon, authenticated;
revoke update, delete, truncate on table public.chat_memory from service_role;

grant select, insert on table public.chat_memory to authenticated;
grant select, insert on table public.chat_memory to service_role;

create index if not exists idx_chat_memory_user_session_created_at
  on public.chat_memory (user_id, session_id, created_at desc);

commit;
