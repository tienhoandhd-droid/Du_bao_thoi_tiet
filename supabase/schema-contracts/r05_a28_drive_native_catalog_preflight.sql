-- R05-A28 READ-ONLY PREFLIGHT — KHÔNG PHẢI MIGRATION, KHÔNG GHI DỮ LIỆU.
-- Mục tiêu: lấy exact live shape trước khi lập change set retire 10 SOP và tạo
-- 12 Drive-native reference records. Chỉ chạy read-only sau khi có Supabase auth.

select
  t.typname as enum_name,
  array_agg(e.enumlabel order by e.enumsortorder) as enum_values
from pg_type t
join pg_namespace n on n.oid = t.typnamespace
join pg_enum e on e.enumtypid = t.oid
where n.nspname = 'public'
  and t.typname in ('document_status', 'document_type', 'source_type', 'language_code')
group by t.typname
order by t.typname;

select
  c.column_name,
  c.data_type,
  c.udt_schema,
  c.udt_name,
  c.is_nullable,
  c.column_default
from information_schema.columns c
where c.table_schema = 'public'
  and c.table_name in ('documents', 'document_versions', 'document_chunks', 'document_access')
order by c.table_name, c.ordinal_position;

select
  d.id,
  d.document_code,
  d.document_title,
  d.status::text as document_status,
  d.approved_for_ai_use,
  d.current_version_id,
  count(distinct dv.id) as version_count,
  count(distinct dc.id) as chunk_count,
  count(distinct da.id) filter (where da.is_active) as active_access_count
from public.documents d
left join public.document_versions dv on dv.document_id = d.id
left join public.document_chunks dc on dc.document_id = d.id
left join public.document_access da on da.document_id = d.id
where d.document_code in (
  'GMP-SOP-001','GMP-SOP-002','GMP-SOP-003','GMP-SOP-004','GMP-SOP-005',
  'GMP-SOP-006','GMP-SOP-007','GMP-SOP-008','GMP-SOP-009','GMP-SOP-010',
  'VQ-QT-003','WHO-TRS-996'
)
group by d.id, d.document_code, d.document_title, d.status,
  d.approved_for_ai_use, d.current_version_id
order by d.document_code;

select
  count(*) as existing_drive_native_code_count,
  array_agg(document_code order by document_code) as existing_drive_native_codes
from public.documents
where document_code like 'REF-%';

select
  con.conname,
  con.contype,
  pg_get_constraintdef(con.oid) as constraint_definition
from pg_constraint con
where con.conrelid in (
  'public.documents'::regclass,
  'public.document_versions'::regclass,
  'public.document_chunks'::regclass,
  'public.document_access'::regclass
)
order by con.conrelid::regclass::text, con.conname;
