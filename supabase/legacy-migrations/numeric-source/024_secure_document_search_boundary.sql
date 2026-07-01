-- CRAVE R01 / Migration 024 — Secure document search boundary
-- Project bắt buộc: bdttccztjtrcaztjgkot
--
-- Mục tiêu:
--   1. Cung cấp RPC typed thay cho dynamic SQL của TKTL WF-06.
--   2. Giữ danh tính JWT của người gọi và RLS bằng SECURITY INVOKER.
--   3. Chỉ trả allowlist metadata; không trả nội dung/chunk hoặc cột ngoài contract.
--
-- KHÔNG tự apply. Chỉ apply sau Claude review và xác nhận exact change set.

begin;

-- Dừng sớm nếu chạy nhầm project/schema hoặc baseline không đúng contract R01.
do $$
declare
  required_column text;
  required_type text;
begin
  if to_regclass('public.documents') is null then
    raise exception 'CRAVE-024: thiếu public.documents; dừng để tránh chạy sai schema.';
  end if;

  if not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'documents'
      and c.relkind = 'r'
      and c.relrowsecurity
  ) then
    raise exception 'CRAVE-024: public.documents phải là bảng đã bật RLS.';
  end if;

  foreach required_column in array array[
    'id', 'document_group_id', 'document_code', 'document_title',
    'document_type', 'language_code', 'source_type', 'version', 'status',
    'approved_for_ai_use', 'translation_status', 'is_ai_translated',
    'owner_department', 'equipment_type', 'equipment_code', 'file_name',
    'file_hash', 'page_count', 'chunk_count', 'uploaded_at', 'reviewed_at',
    'approved_at', 'effective_date'
  ]
  loop
    if not exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'documents'
        and column_name = required_column
    ) then
      raise exception 'CRAVE-024: thiếu public.documents.%; dừng vì contract WF-06 bị drift.',
        required_column;
    end if;
  end loop;

  foreach required_type in array array[
    'document_type', 'source_type', 'language_code', 'document_status',
    'translation_status', 'user_role_name'
  ]
  loop
    if not exists (
      select 1
      from pg_type t
      join pg_namespace n on n.oid = t.typnamespace
      where n.nspname = 'public'
        and t.typname = required_type
    ) then
      raise exception 'CRAVE-024: thiếu type public.%; dừng vì typed RPC không tương thích.',
        required_type;
    end if;
  end loop;

  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-024: thiếu helper public.user_has_any_role(user_role_name[]).';
  end if;

  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    raise exception 'CRAVE-024: thiếu role authenticated.';
  end if;

  if not has_table_privilege('authenticated', 'public.documents', 'SELECT') then
    raise exception 'CRAVE-024: authenticated thiếu SELECT trên public.documents; SECURITY INVOKER không thể hoạt động.';
  end if;

  -- Không âm thầm tạo overload khác khi môi trường đã có function cùng tên.
  if exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'search_documents_v1'
      and p.oid <> coalesce(
        to_regprocedure(
          'public.search_documents_v1(text,public.document_type,public.source_type,public.language_code,public.document_status,text,text,text,public.translation_status,boolean,integer,integer)'
        ),
        0::oid
      )
  ) then
    raise exception 'CRAVE-024: public.search_documents_v1 đã có signature khác; cần review drift trước khi apply.';
  end if;
end
$$;

create or replace function public.search_documents_v1(
  p_keyword text default null,
  p_document_type public.document_type default null,
  p_source_type public.source_type default null,
  p_language_code public.language_code default null,
  p_status public.document_status default null,
  p_equipment_type text default null,
  p_equipment_code text default null,
  p_owner_department text default null,
  p_translation_status public.translation_status default null,
  p_include_superseded boolean default false,
  p_limit integer default 50,
  p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security invoker
set search_path to pg_catalog, public
as $$
declare
  v_keyword text := nullif(btrim(p_keyword), '');
  v_equipment_type text := nullif(btrim(p_equipment_type), '');
  v_equipment_code text := nullif(btrim(p_equipment_code), '');
  v_owner_department text := nullif(btrim(p_owner_department), '');
  v_limit integer := coalesce(p_limit, 50);
  v_offset integer := coalesce(p_offset, 0);
  v_can_view_superseded boolean := false;
  v_result jsonb;
begin
  if auth.uid() is null then
    raise exception using
      errcode = '42501',
      message = 'CRAVE-024: cần JWT người dùng hợp lệ để tìm tài liệu.';
  end if;

  if v_limit < 1 or v_limit > 100 then
    raise exception using
      errcode = '22023',
      message = 'CRAVE-024: p_limit phải nằm trong khoảng 1..100.';
  end if;

  if v_offset < 0 or v_offset > 10000 then
    raise exception using
      errcode = '22023',
      message = 'CRAVE-024: p_offset phải nằm trong khoảng 0..10000.';
  end if;

  if length(v_keyword) > 200
    or length(v_equipment_type) > 100
    or length(v_equipment_code) > 100
    or length(v_owner_department) > 100
  then
    raise exception using
      errcode = '22023',
      message = 'CRAVE-024: bộ lọc text vượt giới hạn cho phép.';
  end if;

  if coalesce(p_include_superseded, false) then
    v_can_view_superseded := public.user_has_any_role(array[
      'admin'::public.user_role_name,
      'qa_manager'::public.user_role_name,
      'auditor'::public.user_role_name
    ]);

    if not coalesce(v_can_view_superseded, false) then
      raise exception using
        errcode = '42501',
        message = 'CRAVE-024: vai trò hiện tại không được xem tài liệu superseded/archived.';
    end if;
  end if;

  with matching as (
    select
      d.id,
      d.document_group_id,
      d.document_code,
      d.document_title,
      d.document_type,
      d.language_code,
      d.source_type,
      d.version,
      d.status,
      d.approved_for_ai_use,
      d.translation_status,
      d.is_ai_translated,
      d.owner_department,
      d.equipment_type,
      d.equipment_code,
      d.file_name,
      d.file_hash,
      d.page_count,
      d.chunk_count,
      d.uploaded_at,
      d.reviewed_at,
      d.approved_at,
      d.effective_date
    from public.documents d
    where (coalesce(p_include_superseded, false) or d.status::text not in ('superseded', 'archived'))
      and (p_document_type is null or d.document_type = p_document_type)
      and (p_source_type is null or d.source_type = p_source_type)
      and (p_language_code is null or d.language_code = p_language_code)
      and (p_status is null or d.status = p_status)
      and (v_equipment_type is null or d.equipment_type = v_equipment_type)
      and (v_equipment_code is null or d.equipment_code = v_equipment_code)
      and (v_owner_department is null or d.owner_department = v_owner_department)
      and (p_translation_status is null or d.translation_status = p_translation_status)
      and (
        v_keyword is null
        or d.document_code ilike '%' || v_keyword || '%'
        or d.document_title ilike '%' || v_keyword || '%'
      )
  ),
  page as (
    select *
    from matching
    order by document_code asc, version desc
    limit v_limit
    offset v_offset
  )
  select jsonb_build_object(
    'documents', coalesce(
      (select jsonb_agg(to_jsonb(page) order by document_code asc, version desc) from page),
      '[]'::jsonb
    ),
    'total_count', (select count(*) from matching),
    'limit', v_limit,
    'offset', v_offset
  )
  into v_result;

  return v_result;
end;
$$;

comment on function public.search_documents_v1(
  text,
  public.document_type,
  public.source_type,
  public.language_code,
  public.document_status,
  text,
  text,
  text,
  public.translation_status,
  boolean,
  integer,
  integer
) is
  'CRAVE-024: metadata search typed cho WF-06; SECURITY INVOKER giữ user JWT/RLS, chỉ trả allowlist cột.';

revoke all privileges on function public.search_documents_v1(
  text,
  public.document_type,
  public.source_type,
  public.language_code,
  public.document_status,
  text,
  text,
  text,
  public.translation_status,
  boolean,
  integer,
  integer
) from public, anon, service_role;

grant execute on function public.search_documents_v1(
  text,
  public.document_type,
  public.source_type,
  public.language_code,
  public.document_status,
  text,
  text,
  text,
  public.translation_status,
  boolean,
  integer,
  integer
) to authenticated;

commit;
