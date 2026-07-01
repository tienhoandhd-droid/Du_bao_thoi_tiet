-- CRAVE - Migration 016: RAG evaluation harness
-- Idempotent: tables, policies and indexes can be created repeatedly.

begin;

do $migration$
begin
  if not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'eval_runs'
      and c.relkind in ('r', 'p')
  ) then
    create table public.eval_runs (
      id uuid primary key default gen_random_uuid(),
      run_at timestamptz default now(),
      model_tag text not null,
      n_questions integer,
      score_mean numeric(5,4),
      score_min numeric(5,4),
      passed boolean,
      notes text
    );
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
      and c.relname = 'eval_results'
      and c.relkind in ('r', 'p')
  ) then
    create table public.eval_results (
      id uuid primary key default gen_random_uuid(),
      run_id uuid references public.eval_runs(id) on delete cascade,
      question_id uuid references public.golden_questions(id) on delete cascade,
      answer text,
      score_faithfulness numeric(5,4),
      score_relevancy numeric(5,4),
      score_context_recall numeric(5,4),
      grounded_pct numeric(5,4),
      passed boolean,
      raw_json jsonb
    );
  end if;
end
$migration$;

alter table public.eval_runs enable row level security;
alter table public.eval_results enable row level security;

revoke all privileges on table public.eval_runs from public, anon;
revoke all privileges on table public.eval_results from public, anon;
grant select, insert on table public.eval_runs to authenticated;
grant select, insert on table public.eval_results to authenticated;

do $policy$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'eval_runs'
      and policyname = 'eval_runs_select_authenticated'
  ) then
    create policy eval_runs_select_authenticated
      on public.eval_runs
      for select
      to authenticated
      using (true);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'eval_runs'
      and policyname = 'eval_runs_insert_authenticated'
  ) then
    create policy eval_runs_insert_authenticated
      on public.eval_runs
      for insert
      to authenticated
      with check (true);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'eval_results'
      and policyname = 'eval_results_select_authenticated'
  ) then
    create policy eval_results_select_authenticated
      on public.eval_results
      for select
      to authenticated
      using (true);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'eval_results'
      and policyname = 'eval_results_insert_authenticated'
  ) then
    create policy eval_results_insert_authenticated
      on public.eval_results
      for insert
      to authenticated
      with check (true);
  end if;
end
$policy$;

create index if not exists idx_eval_results_run_id
  on public.eval_results (run_id);

create index if not exists idx_eval_runs_run_at
  on public.eval_runs (run_at desc);

commit;
