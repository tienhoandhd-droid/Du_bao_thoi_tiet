-- CRAVE deploy migration: 20260701130000_032_crave_claim_verification
-- Semantic source ID: CRAVE-032 / GĐ4.5 Claim Verification foundation
-- Project: bdttccztjtrcaztjgkot
--
-- Tạo nền dữ liệu cho CRAVE (Conflicting Reasoning Approach for explainable claim VErification):
--   * claims            : mệnh đề kiểm chứng được (VI gốc + EN canonical) + khung câu hỏi (PCC/PICO/PECO).
--   * ai_query_sources  : thêm stance/stance_strength để mỗi nguồn trích dẫn mang lập trường 2 chiều.
--   * claim_verdicts    : phán đoán cuối (verdict taxonomy GMP) + confidence + rationale VI + model + escalate.
-- Append-only, RLS read-own-or-auditor, chỉ service_role ghi. Không auto-approve; verdict tới hạn cần human sign-off.

begin;

-- ---------------------------------------------------------------------------
-- Preflight: bảng/hàm bắt buộc + marker tương thích nếu bảng đã tồn tại.
-- ---------------------------------------------------------------------------
do $preflight$
declare
  required_table text;
  target_table text;
  marker text;
begin
  foreach required_table in array array[
    'user_profiles',
    'ai_queries',
    'ai_query_sources',
    'prompt_versions',
    'document_versions',
    'document_chunks'
  ] loop
    if to_regclass(format('public.%I', required_table)) is null then
      raise exception 'CRAVE-032: thiếu bảng bắt buộc public.%.', required_table;
    end if;
  end loop;

  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-032: thiếu user_has_any_role(user_role_name[]).';
  end if;
  if to_regprocedure('public.crave_block_append_only_mutation()') is null then
    raise exception 'CRAVE-032: thiếu crave_block_append_only_mutation().';
  end if;
  if to_regprocedure('gen_random_uuid()') is null then
    raise exception 'CRAVE-032: thiếu gen_random_uuid().';
  end if;

  foreach target_table in array array['claims', 'claim_verdicts'] loop
    if to_regclass(format('public.%I', target_table)) is not null then
      marker := coalesce(obj_description(to_regclass(format('public.%I', target_table)), 'pg_class'), '');
      if marker not like 'CRAVE-032:%' then
        raise exception 'CRAVE-032: public.% đã tồn tại nhưng không có marker tương thích.', target_table;
      end if;
    end if;
  end loop;
end
$preflight$;

-- ---------------------------------------------------------------------------
-- 1) claims — mệnh đề kiểm chứng được, khung hoá PCC/PICO/PECO, song ngữ.
-- ---------------------------------------------------------------------------
create table if not exists public.claims (
  id uuid primary key default gen_random_uuid(),
  query_id uuid references public.ai_queries(id) on update restrict on delete restrict,
  source_question_vi text not null,
  claim_text_vi text not null,
  claim_text_en text not null,
  frame_used text not null
    check (frame_used in ('pcc', 'pico', 'peco')),
  facets jsonb not null default '{}'::jsonb
    check (jsonb_typeof(facets) = 'object'),
  created_by uuid references public.user_profiles(id) on update restrict on delete restrict,
  created_at timestamptz not null default now(),
  constraint claims_text_not_blank
    check (length(btrim(claim_text_vi)) > 0 and length(btrim(claim_text_en)) > 0)
);

comment on table public.claims is
  'CRAVE-032: append-only claim record. Câu hỏi VI -> mệnh đề kiểm chứng được (VI gốc + EN canonical) khung hoá PCC/PICO/PECO cho retrieval song ngữ.';
comment on column public.claims.frame_used is
  'CRAVE-032: khung câu hỏi đã dùng — pcc (mặc định), pico (so sánh 2 phương án), peco (phơi nhiễm/điều kiện).';
comment on column public.claims.facets is
  'CRAVE-032: facet đã trích (population/concept/context/comparison/exposure/outcome/threshold/doc_type) làm khoá metadata.';
comment on column public.claims.claim_text_en is
  'CRAVE-032: mệnh đề EN canonical (qua glossary) — khoá retrieval; VI gốc giữ để audit.';

-- ---------------------------------------------------------------------------
-- 2) ai_query_sources — thêm lập trường 2 chiều cho mỗi nguồn trích dẫn.
--    Bảng đã có append-only guard + lineage trigger (CRAVE-030B); chỉ ADD cột.
-- ---------------------------------------------------------------------------
alter table public.ai_query_sources
  add column if not exists stance text,
  add column if not exists stance_strength numeric;

do $ai_query_sources_constraints$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_stance_check'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_stance_check
      check (stance is null or stance in ('support', 'refute', 'limiting', 'neutral'));
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_query_sources'::regclass
      and conname = 'ai_query_sources_stance_strength_check'
  ) then
    alter table public.ai_query_sources
      add constraint ai_query_sources_stance_strength_check
      check (stance_strength is null or (stance_strength >= 0 and stance_strength <= 1));
  end if;
end
$ai_query_sources_constraints$;

comment on column public.ai_query_sources.stance is
  'CRAVE-032: lập trường của nguồn so với claim — support/refute/limiting/neutral. Set khi INSERT (bảng append-only).';
comment on column public.ai_query_sources.stance_strength is
  'CRAVE-032: độ mạnh lập trường 0..1 do Support/Refute-agent đánh giá.';

-- ---------------------------------------------------------------------------
-- 3) claim_verdicts — phán đoán cuối của Judge (taxonomy GMP), immutable.
-- ---------------------------------------------------------------------------
create table if not exists public.claim_verdicts (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references public.claims(id) on update restrict on delete restrict,
  verdict text not null
    check (verdict in ('supported', 'conditional', 'conflicting', 'outdated', 'insufficient')),
  confidence numeric not null
    check (confidence >= 0 and confidence <= 1),
  rationale_vi text not null
    check (length(btrim(rationale_vi)) > 0),
  support_count integer not null default 0 check (support_count >= 0),
  refute_count integer not null default 0 check (refute_count >= 0),
  model_provider text not null,
  model_name text not null,
  escalated boolean not null default false,
  escalation_target text
    check (escalation_target is null or escalation_target in ('openai', 'human')),
  requires_human_signoff boolean not null default false,
  prompt_version_id uuid references public.prompt_versions(id) on update restrict on delete restrict,
  created_at timestamptz not null default now(),
  constraint claim_verdicts_escalation_consistency
    check (escalated = (escalation_target is not null))
);

comment on table public.claim_verdicts is
  'CRAVE-032: append-only verdict của Judge cho một claim. Taxonomy GMP; conflicting/insufficient hoặc escalate => requires_human_signoff. AI chỉ tạo DRAFT.';
comment on column public.claim_verdicts.verdict is
  'CRAVE-032: supported | conditional | conflicting | outdated | insufficient.';
comment on column public.claim_verdicts.requires_human_signoff is
  'CRAVE-032: true khi verdict tới hạn (conflicting/insufficient) hoặc đã escalate — bắt buộc người có thẩm quyền duyệt trước khi dùng.';

-- ---------------------------------------------------------------------------
-- Index
-- ---------------------------------------------------------------------------
create index if not exists idx_claims_query
  on public.claims (query_id) where query_id is not null;
create index if not exists idx_claims_created_by
  on public.claims (created_by, created_at desc);
create index if not exists idx_claim_verdicts_claim
  on public.claim_verdicts (claim_id, created_at desc);
create index if not exists idx_claim_verdicts_verdict
  on public.claim_verdicts (verdict, created_at desc);
create index if not exists idx_claim_verdicts_signoff
  on public.claim_verdicts (requires_human_signoff, created_at desc)
  where requires_human_signoff;
create index if not exists idx_ai_query_sources_stance
  on public.ai_query_sources (query_id, stance) where stance is not null;

-- ---------------------------------------------------------------------------
-- RLS + grants: chỉ service_role ghi; authenticated chỉ select own-or-auditor.
-- ---------------------------------------------------------------------------
alter table public.claims enable row level security;
alter table public.claim_verdicts enable row level security;

revoke all on table public.claims, public.claim_verdicts from public, anon, authenticated;
grant select on table public.claims, public.claim_verdicts to authenticated;

do $policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'claims'
      and policyname = 'claims_read_own_or_auditor'
  ) then
    create policy claims_read_own_or_auditor
      on public.claims for select to authenticated
      using (
        created_by = auth.uid()
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'claim_verdicts'
      and policyname = 'claim_verdicts_read_own_or_auditor'
  ) then
    create policy claim_verdicts_read_own_or_auditor
      on public.claim_verdicts for select to authenticated
      using (
        exists (
          select 1 from public.claims c
          where c.id = claim_id and c.created_by = auth.uid()
        )
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;
end
$policies$;

-- ---------------------------------------------------------------------------
-- Append-only guard: chặn UPDATE/DELETE/TRUNCATE (evidence bất biến).
-- ---------------------------------------------------------------------------
do $append_only_triggers$
declare
  target_table text;
  trigger_name text;
begin
  foreach target_table in array array['claims', 'claim_verdicts'] loop
    trigger_name := target_table || '_append_only_guard';
    if exists (
      select 1 from pg_trigger trigger_row
      where trigger_row.tgrelid = to_regclass(format('public.%I', target_table))
        and trigger_row.tgname = trigger_name
        and trigger_row.tgfoid <> to_regprocedure('public.crave_block_append_only_mutation()')
    ) then
      raise exception 'CRAVE-032: trigger % trên public.% không tương thích.', trigger_name, target_table;
    end if;
    if not exists (
      select 1 from pg_trigger trigger_row
      where trigger_row.tgrelid = to_regclass(format('public.%I', target_table))
        and trigger_row.tgname = trigger_name
    ) then
      execute format(
        'create trigger %I before update or delete or truncate on public.%I '
        'for each statement execute function public.crave_block_append_only_mutation()',
        trigger_name, target_table
      );
    end if;
  end loop;
end
$append_only_triggers$;

-- ---------------------------------------------------------------------------
-- Final assert
-- ---------------------------------------------------------------------------
do $final_assert$
declare
  target_table text;
  missing_rls bigint;
begin
  foreach target_table in array array['claims', 'claim_verdicts'] loop
    select count(*) into missing_rls
    from pg_class
    where oid = to_regclass(format('public.%I', target_table)) and relrowsecurity is false;
    if missing_rls > 0 then
      raise exception 'CRAVE-032: RLS chưa bật trên public.%.', target_table;
    end if;
  end loop;

  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'ai_query_sources' and column_name = 'stance'
  ) then
    raise exception 'CRAVE-032: thiếu cột ai_query_sources.stance sau migration.';
  end if;
end
$final_assert$;

commit;
