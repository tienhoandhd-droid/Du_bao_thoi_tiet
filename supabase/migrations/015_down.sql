-- Rollback CRAVE Platform Alignment - Migration 015
-- CẢNH BÁO: rollback này khôi phục quyền cũ, gồm cả các quyền đã bị đánh giá
-- không an toàn. Chỉ chạy khi có phê duyệt và có kế hoạch cô lập hệ thống.

begin;

drop trigger if exists audit_log_append_only_guard on public.audit_log;
drop trigger if exists chat_memory_append_only_guard on public.chat_memory;

drop index if exists public.idx_chat_memory_user_session_created_at;

drop function if exists public.crave_block_append_only_mutation();

alter view public.documents_effective
  reset (security_invoker);

alter view public.documents_due_for_review
  reset (security_invoker);

alter view public.documents_review_soon
  reset (security_invoker);

grant select on table public.documents_effective to anon, authenticated, service_role;
grant select on table public.documents_due_for_review to anon, authenticated, service_role;
grant select on table public.documents_review_soon to anon, authenticated, service_role;

-- Khôi phục quyền EXECUTE public trước migration 015.
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
      'grant execute on function %s to public',
      function_signature
    );
  end loop;
end
$$;

-- Trả search_path về trạng thái mặc định trước migration 015.
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
      'alter function %s reset search_path',
      function_signature
    );
  end loop;
end
$$;

-- Khôi phục effective privileges cũ của audit_log và policy INSERT public.
-- Cũng khôi phục view_audit_log về scope {public} như trước migration 015.
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
      to public
      using (user_has_any_role(array['admin'::user_role_name, 'qa_manager'::user_role_name, 'auditor'::user_role_name]));
  end if;
end
$$;

grant all privileges on table public.audit_log to anon, authenticated, service_role;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'audit_log'
      and policyname = 'insert_audit_log'
  ) then
    create policy insert_audit_log
      on public.audit_log
      for insert
      to public
      with check (true);
  end if;
end
$$;

-- Khôi phục effective privileges cũ của chat_memory.
grant all privileges on table public.chat_memory to anon, authenticated, service_role;

commit;
