-- CRAVE Chat 11 - Migration 014: bộ nhớ hội thoại cho WF-12
-- Chỉ tạo cấu trúc local; chưa được áp dụng lên project bdttccztjtrcaztjgkot.

begin;

create table if not exists public.chat_memory (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null,
  user_id     uuid not null,
  role        text not null
              constraint chat_memory_role_check
              check (role in ('user', 'assistant', 'tool')),
  content     text not null,
  created_at  timestamptz not null default now(),
  tokens_used integer not null default 0
              constraint chat_memory_tokens_used_nonnegative
              check (tokens_used >= 0)
);

comment on table public.chat_memory is
  'CRAVE-014: bộ nhớ hội thoại append-only theo session cho trợ lý QA agentic.';

create index if not exists idx_chat_memory_session_created_at
  on public.chat_memory (session_id, created_at);

create index if not exists idx_chat_memory_user_id
  on public.chat_memory (user_id);

alter table public.chat_memory enable row level security;

grant select, insert on table public.chat_memory to authenticated;
grant select, insert on table public.chat_memory to service_role;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'chat_memory'
      and policyname = 'chat_memory_insert_authenticated'
  ) then
    create policy chat_memory_insert_authenticated
      on public.chat_memory
      for insert
      to authenticated
      with check (user_id = auth.uid());
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'chat_memory'
      and policyname = 'chat_memory_select_own_session'
  ) then
    create policy chat_memory_select_own_session
      on public.chat_memory
      for select
      to authenticated
      using (user_id = auth.uid());
  end if;
end
$$;

commit;

