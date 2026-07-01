-- CRAVE Chat 17 - Migration 020: phiên làm việc Validation Copilot.
-- Chỉ tạo cấu trúc local; KHÔNG tự apply lên project bdttccztjtrcaztjgkot.

begin;

-- Dừng sớm nếu migration nền chưa được áp dụng hoặc đang chạy nhầm schema.
do $preflight$
begin
  if to_regclass('auth.users') is null then
    raise exception 'CRAVE-020: thiếu bảng auth.users; dừng để tránh tạo khóa ngoại sai.';
  end if;

  if to_regclass('public.validation_templates') is null then
    raise exception 'CRAVE-020: thiếu bảng public.validation_templates; cần áp dụng migration nền trước 020.';
  end if;

  if to_regprocedure('public.update_updated_at()') is null then
    raise exception 'CRAVE-020: thiếu hàm public.update_updated_at(); cần áp dụng migration nền trước 020.';
  end if;

  if to_regprocedure('public.crave_block_append_only_mutation()') is null then
    raise exception 'CRAVE-020: thiếu hàm public.crave_block_append_only_mutation(); cần áp dụng migration 015 trước 020.';
  end if;
end
$preflight$;

create table if not exists public.validation_sessions (
  id uuid primary key default gen_random_uuid(),
  created_by uuid not null references auth.users(id),
  equipment_code text not null,
  validation_type text not null
    constraint validation_sessions_validation_type_check
    check (validation_type in ('iq', 'oq', 'pq')),
  template_id uuid not null references public.validation_templates(id),
  session_data jsonb not null default '{}'::jsonb,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint validation_sessions_equipment_code_not_blank
    check (btrim(equipment_code) <> ''),
  constraint validation_sessions_session_data_object
    check (jsonb_typeof(session_data) = 'object')
);

comment on table public.validation_sessions is
  'CRAVE-020: phiên làm việc của Validation Copilot theo thiết bị và loại thẩm định.';

create table if not exists public.session_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.validation_sessions(id),
  role text not null
    constraint session_messages_role_check
    check (role in ('user', 'assistant')),
  content text not null,
  cited_chunk_ids uuid[] not null default '{}'::uuid[],
  grounded boolean not null default false,
  created_at timestamptz not null default now(),
  constraint session_messages_content_not_blank
    check (btrim(content) <> ''),
  constraint session_messages_grounded_requires_citation
    check (grounded = false or cardinality(cited_chunk_ids) > 0)
);

comment on table public.session_messages is
  'CRAVE-020: lịch sử trao đổi append-only của Validation Copilot.';

create index if not exists idx_session_messages_session_created_at
  on public.session_messages (session_id, created_at);

alter table public.validation_sessions enable row level security;
alter table public.session_messages enable row level security;

revoke all privileges on table public.validation_sessions
  from public, anon, authenticated;
revoke all privileges on table public.session_messages
  from public, anon, authenticated;

grant select, insert on table public.validation_sessions to authenticated;
grant select, insert on table public.session_messages to authenticated;

-- Người dùng đã xác thực chỉ được tạo và đọc phiên của chính mình.
do $policies$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'validation_sessions'
      and policyname = 'validation_sessions_select_own'
  ) then
    create policy validation_sessions_select_own
      on public.validation_sessions
      for select
      to authenticated
      using (created_by = auth.uid());
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'validation_sessions'
      and policyname = 'validation_sessions_insert_own'
  ) then
    create policy validation_sessions_insert_own
      on public.validation_sessions
      for insert
      to authenticated
      with check (created_by = auth.uid());
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'session_messages'
      and policyname = 'session_messages_select_own_session'
  ) then
    create policy session_messages_select_own_session
      on public.session_messages
      for select
      to authenticated
      using (
        exists (
          select 1
          from public.validation_sessions session_owner
          where session_owner.id = session_messages.session_id
            and session_owner.created_by = auth.uid()
        )
      );
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'session_messages'
      and policyname = 'session_messages_insert_own_session'
  ) then
    create policy session_messages_insert_own_session
      on public.session_messages
      for insert
      to authenticated
      with check (
        exists (
          select 1
          from public.validation_sessions session_owner
          where session_owner.id = session_messages.session_id
            and session_owner.created_by = auth.uid()
        )
      );
  end if;
end
$policies$;

-- Giữ updated_at đúng khi backend tin cậy thay đổi trạng thái/session_data.
do $triggers$
begin
  if not exists (
    select 1
    from pg_trigger
    where tgrelid = 'public.validation_sessions'::regclass
      and tgname = 'validation_sessions_set_updated_at'
      and not tgisinternal
  ) then
    create trigger validation_sessions_set_updated_at
      before update on public.validation_sessions
      for each row
      execute function public.update_updated_at();
  end if;

  if not exists (
    select 1
    from pg_trigger
    where tgrelid = 'public.session_messages'::regclass
      and tgname = 'session_messages_append_only_guard'
      and not tgisinternal
  ) then
    create trigger session_messages_append_only_guard
      before update or delete or truncate on public.session_messages
      for each statement
      execute function public.crave_block_append_only_mutation();
  end if;
end
$triggers$;

commit;
