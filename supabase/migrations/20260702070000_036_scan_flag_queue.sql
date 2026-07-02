-- CRAVE deploy migration: 20260702070000_036_scan_flag_queue
-- Semantic source ID: CRAVE-036 / AL provisional-approve + hàng đợi cờ chờ người duyệt
-- Project: bdttccztjtrcaztjgkot
--
-- Bậc [4]-[5] của luật high-accuracy-ensemble:
--   Khi quét đa engine + retry (DPI ladder) vẫn chưa đồng thuận, panel AL
--   (MoA free) DUYỆT TẠM (provisional) để KHÔNG NGHẼN hệ thống — tài liệu đi
--   tiếp — NHƯNG mọi mục bị gắn cờ được LƯU vào scan_flag_queue, trạng thái
--   AL_PROVISIONAL_PENDING_HUMAN, chờ người có thẩm quyền duyệt.
--   Người duyệt gọi clear_scan_flag(): HUMAN_APPROVED => BỎ CỜ (rời danh sách
--   pending); HUMAN_REJECTED => thu hồi provisional, chặn AI use.
-- Chỉ authenticated admin/qa_manager mới clear được (human sign-off thật, không
-- để automation tự duyệt). UPDATE trực tiếp bị chặn; chỉ qua hàm SECURITY DEFINER.

begin;

do $preflight$
begin
  if to_regclass('public.user_profiles') is null then
    raise exception 'CRAVE-036: thiếu bảng public.user_profiles.';
  end if;
  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-036: thiếu user_has_any_role(user_role_name[]).';
  end if;
  if to_regprocedure('gen_random_uuid()') is null then
    raise exception 'CRAVE-036: thiếu gen_random_uuid().';
  end if;
  if to_regclass('public.scan_flag_queue') is not null then
    if coalesce(obj_description(to_regclass('public.scan_flag_queue'), 'pg_class'), '') not like 'CRAVE-036:%' then
      raise exception 'CRAVE-036: public.scan_flag_queue đã tồn tại nhưng thiếu marker tương thích.';
    end if;
  end if;
end
$preflight$;

-- ---------------------------------------------------------------------------
-- 1) scan_flag_queue — danh sách cờ AL provisional chờ người duyệt.
-- ---------------------------------------------------------------------------
create table if not exists public.scan_flag_queue (
  id uuid primary key default gen_random_uuid(),
  document_code text not null,
  source_sha256 text,
  page_number integer,
  gate text not null default 'CRAVE_SCAN_GATE_V3',
  engines_evidence jsonb not null default '{}'::jsonb
    check (jsonb_typeof(engines_evidence) = 'object'),
  al_verdict text not null default 'provisional_approved'
    check (al_verdict in ('provisional_approved', 'mismatch_flagged')),
  al_confidence numeric
    check (al_confidence is null or (al_confidence >= 0 and al_confidence <= 1)),
  al_mismatch jsonb not null default '[]'::jsonb
    check (jsonb_typeof(al_mismatch) = 'array'),
  provisional_approved boolean not null default true,
  ai_use_allowed boolean not null default true,
  status text not null default 'AL_PROVISIONAL_PENDING_HUMAN'
    check (status in ('AL_PROVISIONAL_PENDING_HUMAN', 'HUMAN_APPROVED', 'HUMAN_REJECTED')),
  created_by uuid references public.user_profiles(id) on update restrict on delete restrict,
  created_at timestamptz not null default now(),
  reviewed_by uuid references public.user_profiles(id) on update restrict on delete restrict,
  reviewed_at timestamptz,
  review_note text,
  constraint scan_flag_review_consistency
    check (
      (status = 'AL_PROVISIONAL_PENDING_HUMAN' and reviewed_by is null and reviewed_at is null)
      or (status in ('HUMAN_APPROVED', 'HUMAN_REJECTED') and reviewed_by is not null and reviewed_at is not null)
    )
);

comment on table public.scan_flag_queue is
  'CRAVE-036: hàng đợi cờ AL provisional. AL duyệt tạm để không nghẽn; mỗi cờ chờ người duyệt. HUMAN_APPROVED = bỏ cờ; HUMAN_REJECTED = thu hồi.';
comment on column public.scan_flag_queue.al_mismatch is
  'CRAVE-036: danh sách trường "dữ liệu không khớp" AL phát hiện so với bản gốc (mỗi phần tử: {field, engine_values, note}).';
comment on column public.scan_flag_queue.provisional_approved is
  'CRAVE-036: true = AL cho đi tiếp tạm thời; đổi false khi HUMAN_REJECTED.';
comment on column public.scan_flag_queue.status is
  'CRAVE-036: AL_PROVISIONAL_PENDING_HUMAN (đang gắn cờ) | HUMAN_APPROVED (bỏ cờ) | HUMAN_REJECTED (thu hồi).';

create index if not exists idx_scan_flag_pending
  on public.scan_flag_queue (status, created_at desc)
  where status = 'AL_PROVISIONAL_PENDING_HUMAN';
create index if not exists idx_scan_flag_doc
  on public.scan_flag_queue (document_code, page_number);

-- ---------------------------------------------------------------------------
-- 2) View danh sách cờ đang chờ duyệt (bỏ cờ = rời view này).
-- ---------------------------------------------------------------------------
create or replace view public.scan_flags_pending as
  select id, document_code, source_sha256, page_number, gate,
         al_verdict, al_confidence, al_mismatch, created_at
  from public.scan_flag_queue
  where status = 'AL_PROVISIONAL_PENDING_HUMAN';

comment on view public.scan_flags_pending is
  'CRAVE-036: danh sách cờ AL provisional CHỜ người duyệt. Duyệt xong (clear_scan_flag) sẽ rời khỏi view.';

-- ---------------------------------------------------------------------------
-- 3) RLS: authenticated admin/qa/auditor đọc; ghi qua service_role/hàm.
-- ---------------------------------------------------------------------------
alter table public.scan_flag_queue enable row level security;
revoke all on table public.scan_flag_queue from public, anon, authenticated;
grant select on table public.scan_flag_queue to authenticated;
grant select on public.scan_flags_pending to authenticated;

do $policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'scan_flag_queue'
      and policyname = 'scan_flag_read_reviewer'
  ) then
    create policy scan_flag_read_reviewer
      on public.scan_flag_queue for select to authenticated
      using (
        created_by = auth.uid()
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
-- 4) clear_scan_flag — người duyệt bỏ cờ / thu hồi. Chỉ admin/qa_manager.
-- ---------------------------------------------------------------------------
create or replace function public.clear_scan_flag(
  p_flag_id uuid,
  p_decision text,
  p_note text default null
)
returns public.scan_flag_queue
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_row public.scan_flag_queue;
begin
  if p_decision not in ('HUMAN_APPROVED', 'HUMAN_REJECTED') then
    raise exception 'clear_scan_flag: decision phải là HUMAN_APPROVED hoặc HUMAN_REJECTED (nhận %).', p_decision;
  end if;
  if not public.user_has_any_role(array[
       'admin'::public.user_role_name,
       'qa_manager'::public.user_role_name]) then
    raise exception 'clear_scan_flag: chỉ admin/qa_manager mới được duyệt cờ (human sign-off).';
  end if;

  update public.scan_flag_queue
     set status = p_decision,
         provisional_approved = (p_decision = 'HUMAN_APPROVED'),
         ai_use_allowed = (p_decision = 'HUMAN_APPROVED'),
         reviewed_by = auth.uid(),
         reviewed_at = now(),
         review_note = p_note
   where id = p_flag_id
     and status = 'AL_PROVISIONAL_PENDING_HUMAN'
   returning * into v_row;

  if not found then
    raise exception 'clear_scan_flag: không có cờ pending với id % (có thể đã được duyệt).', p_flag_id;
  end if;
  return v_row;
end
$$;

comment on function public.clear_scan_flag(uuid, text, text) is
  'CRAVE-036: người có thẩm quyền (admin/qa_manager) duyệt cờ. HUMAN_APPROVED => bỏ cờ (rời scan_flags_pending); HUMAN_REJECTED => thu hồi provisional + chặn ai_use. Chặn UPDATE trực tiếp.';

revoke all on function public.clear_scan_flag(uuid, text, text) from public, anon;
grant execute on function public.clear_scan_flag(uuid, text, text) to authenticated, service_role;

-- Chặn UPDATE/DELETE trực tiếp của authenticated (chỉ đọc + qua hàm definer).
-- (Không có grant UPDATE/DELETE cho authenticated ở trên nên đã fail-closed.)

commit;
