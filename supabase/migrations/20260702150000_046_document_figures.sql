-- CRAVE deploy migration: 20260702150000_046_document_figures
-- Semantic source ID: CRAVE-046 / multimodal figures: schema + bucket private + RLS + dedup
-- Project: bdttccztjtrcaztjgkot
--
-- Nền tảng lưu HÌNH/SƠ ĐỒ/BẢNG (M-A #1). Ảnh crop → Supabase Storage (private
-- bucket 'doc-figures'); metadata + bbox + caption + embedding → bảng dưới.
-- Retrieval "gõ chữ ra hình": caption_embedding(1536) tái dùng model text hiện có
-- (Lớp 1) + visual_embedding(768) để dành (Lớp 3). Ensemble: detected_by/agreement.
-- Bảo mật GitHub Pages tĩnh: RLS + signed URL, KHÔNG service_role frontend.

begin;

do $guard$
begin
  if to_regclass('public.documents') is null or to_regclass('public.document_versions') is null then
    raise exception 'CRAVE-046: thiếu documents/document_versions.';
  end if;
end
$guard$;

-- (1) document_figures ----------------------------------------------------
create table if not exists public.document_figures (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  document_code text not null,
  document_version text,
  document_version_id uuid references public.document_versions(id),
  page_number integer not null,
  figure_index integer not null default 0,
  element_class text not null default 'picture'
    check (element_class in ('picture','diagram','flowchart','formula','chart','table','image')),
  bbox jsonb,                       -- {x,y,w,h} chuẩn hoá 0..1
  storage_path text,                -- webp full trong bucket doc-figures
  thumb_path text,                  -- webp thumbnail (pre-gen, không phụ thuộc gói Pro)
  caption text,
  labels text[] not null default '{}',
  ocr_text text,
  detected_by text[] not null default '{}',   -- engine phát hiện (ensemble)
  agreement integer not null default 1,        -- số engine đồng thuận (IoU)
  review_status text not null default 'al_provisional'
    check (review_status in ('consensus','al_provisional','human_approved','rejected')),
  al_reviewer text,
  source_sha256 text,
  crop_sha256 text,
  caption_embedding extensions.vector(1536),   -- Lớp 1: text→hình (tái dùng 1536)
  visual_embedding extensions.vector(768),     -- Lớp 3: visual (để dành)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_code, document_version, page_number, figure_index)
);
comment on table public.document_figures is
  'CRAVE-046: hình/sơ đồ/công thức trích từ tài liệu. Ảnh ở bucket doc-figures; caption_embedding cho text→hình; ensemble detected_by/agreement; review_status vòng đời.';

create unique index if not exists uq_document_figures_crop_sha256
  on public.document_figures (crop_sha256) where crop_sha256 is not null;   -- chống trùng crop
create index if not exists idx_document_figures_doc on public.document_figures (document_id, page_number);
create index if not exists idx_document_figures_pending on public.document_figures (review_status) where review_status <> 'human_approved';

-- (2) document_tables -----------------------------------------------------
create table if not exists public.document_tables (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  document_code text not null,
  document_version text,
  page_number integer not null,
  table_index integer not null default 0,
  n_rows integer,
  n_cols integer,
  cells jsonb,                      -- cấu trúc ô để tra cứu số liệu
  markdown text,                    -- render HTML/markdown
  storage_path text,                -- optional crop ảnh bảng để đối chiếu
  caption text,
  ocr_text text,
  detected_by text[] not null default '{}',
  agreement integer not null default 1,
  review_status text not null default 'al_provisional'
    check (review_status in ('consensus','al_provisional','human_approved','rejected')),
  source_sha256 text,
  crop_sha256 text,
  caption_embedding extensions.vector(1536),
  created_at timestamptz not null default now(),
  unique (document_code, document_version, page_number, table_index)
);
comment on table public.document_tables is
  'CRAVE-046: bảng trích từ tài liệu — cells jsonb (giữ số liệu) + markdown + optional crop.';
create unique index if not exists uq_document_tables_crop_sha256
  on public.document_tables (crop_sha256) where crop_sha256 is not null;
create index if not exists idx_document_tables_doc on public.document_tables (document_id, page_number);

-- (3) RLS: authenticated CHỈ đọc hình của tài liệu đã duyệt AI; ghi = service_role
alter table public.document_figures enable row level security;
alter table public.document_tables  enable row level security;

drop policy if exists figures_read_approved on public.document_figures;
create policy figures_read_approved on public.document_figures for select to authenticated
  using (exists (select 1 from public.documents d where d.id = document_id and d.approved_for_ai_use = true));

drop policy if exists tables_read_approved on public.document_tables;
create policy tables_read_approved on public.document_tables for select to authenticated
  using (exists (select 1 from public.documents d where d.id = document_id and d.approved_for_ai_use = true));

grant select on public.document_figures, public.document_tables to authenticated;
grant all on public.document_figures, public.document_tables to service_role;

-- (4) Storage bucket private + RLS storage.objects
insert into storage.buckets (id, name, public) values ('doc-figures','doc-figures', false)
on conflict (id) do nothing;

drop policy if exists doc_figures_read_auth on storage.objects;
create policy doc_figures_read_auth on storage.objects for select to authenticated
  using (bucket_id = 'doc-figures');
-- upload/update/delete: KHÔNG cấp cho authenticated → chỉ service_role (bypass RLS) ghi.

commit;
