-- CRAVE Chat 10 - Citation Grounding
-- Mục tiêu: lưu từng khẳng định AI cùng chunk_id nguồn; khẳng định không có nguồn phải grounded = false.

begin;

do $$
begin
  if to_regclass('public.ai_query_sources') is null then
    raise exception 'Thiếu bảng public.ai_query_sources; cần chạy các migration nền trước 013_citation_grounding.';
  end if;

  if to_regclass('public.document_chunks') is null then
    raise exception 'Thiếu bảng public.document_chunks; citation grounding cần bảng chunk nguồn.';
  end if;
end
$$;

alter table public.ai_query_sources enable row level security;

do $$
begin
  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'ai_query_sources'
      and column_name = 'chunk_id'
  ) then
    alter table public.ai_query_sources
      add column chunk_id uuid;

    comment on column public.ai_query_sources.chunk_id is
      'CRAVE-013: ID chunk tài liệu dùng làm nguồn cho khẳng định AI.';
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'ai_query_sources'
      and column_name = 'claim_text'
  ) then
    alter table public.ai_query_sources
      add column claim_text text;

    comment on column public.ai_query_sources.claim_text is
      'CRAVE-013: Nội dung khẳng định được AI tách ra để kiểm nguồn.';
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'ai_query_sources'
      and column_name = 'grounded'
  ) then
    alter table public.ai_query_sources
      add column grounded boolean not null default false;

    comment on column public.ai_query_sources.grounded is
      'CRAVE-013: true khi khẳng định có chunk_id nguồn hợp lệ; false khi chưa có nguồn.';
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'ai_query_sources'
      and column_name = 'citation_rank'
  ) then
    alter table public.ai_query_sources
      add column citation_rank integer;

    comment on column public.ai_query_sources.citation_rank is
      'CRAVE-013: Thứ tự trích dẫn của claim trong câu trả lời AI.';
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_grounded_requires_chunk'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_grounded_requires_chunk
      check (grounded = false or chunk_id is not null);
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_claim_text_not_blank'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_claim_text_not_blank
      check (claim_text is null or btrim(claim_text) <> '');
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_citation_rank_positive'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_citation_rank_positive
      check (citation_rank is null or citation_rank > 0);
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint con
    join pg_attribute att
      on att.attrelid = con.conrelid
     and att.attnum = any(con.conkey)
    where con.conrelid = 'public.ai_query_sources'::regclass
      and con.contype = 'f'
      and att.attname = 'chunk_id'
      and con.confrelid = 'public.document_chunks'::regclass
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_cg_chunk_id_fkey
      foreign key (chunk_id)
      references public.document_chunks(id)
      on delete set null;
  end if;
end
$$;

create index if not exists idx_ai_query_sources_cg_chunk_id
  on public.ai_query_sources (chunk_id)
  where chunk_id is not null;

create index if not exists idx_ai_query_sources_cg_query_rank
  on public.ai_query_sources (query_id, citation_rank)
  where claim_text is not null;

create index if not exists idx_ai_query_sources_cg_ungrounded
  on public.ai_query_sources (query_id)
  where grounded = false;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'ai_query_sources'
      and policyname = 'insert_ai_query_sources_citation_grounding'
  ) then
    create policy insert_ai_query_sources_citation_grounding
      on public.ai_query_sources
      for insert
      to authenticated
      with check (
        exists (
          select 1
          from public.ai_queries q
          where q.id = ai_query_sources.query_id
            and (
              q.user_id = auth.uid()
              or public.user_has_any_role(array[
                'admin'::public.user_role_name,
                'qa_manager'::public.user_role_name,
                'validation'::public.user_role_name
              ])
            )
        )
      );
  end if;
end
$$;

commit;
