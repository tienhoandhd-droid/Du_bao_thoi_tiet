-- CRAVE deploy migration: 20260702130000_044_multiquery_rrf_glossary
-- Semantic source ID: CRAVE-044 / Multi-Query song song + RRF tầng-2 + glossary GMP VI↔EN
-- Project: bdttccztjtrcaztjgkot
--
-- Áp nguyên tắc "song song + tổng hợp" vào RETRIEVAL (khoảng trống đã audit):
--   (1) gmp_glossary: từ điển đồng nghĩa GMP Việt↔Anh cho query expansion + FTS.
--   (2) hybrid_search_multi_v1: nhận N biến thể (embeddings[] + fts_queries[]),
--       chạy hybrid_search_v4 cho TỪNG biến thể (mỗi biến thể tự RRF vector+FTS),
--       rồi RRF TẦNG-2 hợp nhất N danh sách (1/(k+rank)) → top-k.
--   Fail-closed giữ nguyên: delegate hoàn toàn cho v4 (cổng version/chunk/permission).

begin;

-- (1) Glossary GMP VI↔EN --------------------------------------------------
create table if not exists public.gmp_glossary (
  id uuid primary key default gen_random_uuid(),
  term_vi text not null,
  term_en text,
  synonyms text[] not null default '{}',
  domain text,
  created_at timestamptz not null default now(),
  unique (term_vi)
);
comment on table public.gmp_glossary is
  'CRAVE-044: từ điển đồng nghĩa GMP Việt↔Anh — dùng cho query expansion + FTS tiếng Việt.';

insert into public.gmp_glossary (term_vi, term_en, synonyms, domain) values
  ('thẩm định', 'validation', array['xác nhận giá trị sử dụng','đánh giá','validate'], 'validation'),
  ('hiệu chuẩn', 'calibration', array['định chuẩn','calibrate'], 'metrology'),
  ('thẩm định lắp đặt', 'installation qualification', array['IQ'], 'qualification'),
  ('thẩm định vận hành', 'operational qualification', array['OQ'], 'qualification'),
  ('thẩm định hiệu năng', 'performance qualification', array['PQ'], 'qualification'),
  ('độ sạch', 'cleanliness', array['cấp độ sạch','phân loại độ sạch'], 'cleanroom'),
  ('phòng sạch', 'cleanroom', array['cấp sạch','grade','class'], 'cleanroom'),
  ('tủ an toàn sinh học', 'biosafety cabinet', array['BSC','tủ ATSH','cabinet an toàn sinh học'], 'equipment'),
  ('vận tốc gió', 'air velocity', array['tốc độ gió','vận tốc dòng khí','airflow velocity'], 'hvac'),
  ('chênh áp', 'pressure differential', array['chênh lệch áp suất','differential pressure','áp suất chênh'], 'hvac'),
  ('màng lọc HEPA', 'HEPA filter', array['lọc HEPA','bộ lọc HEPA'], 'hvac'),
  ('vô trùng', 'aseptic', array['chiết rót vô trùng','điều kiện vô trùng'], 'sterile'),
  ('tiệt trùng', 'sterilization', array['khử trùng','sterilize'], 'sterile'),
  ('chuỗi lạnh', 'cold chain', array['bảo quản lạnh','dây chuyền lạnh'], 'distribution'),
  ('độ kín', 'integrity', array['tính toàn vẹn','kiểm tra độ kín','integrity test'], 'testing'),
  ('nhiễm chéo', 'cross contamination', array['nhiễm chéo','contamination'], 'quality'),
  ('truy xuất nguồn gốc', 'traceability', array['truy vết','lineage'], 'quality'),
  ('sai lệch', 'deviation', array['độ lệch','deviation'], 'quality'),
  ('kiểm soát thay đổi', 'change control', array['quản lý thay đổi','change management'], 'quality'),
  ('thực hành sản xuất tốt', 'good manufacturing practice', array['GMP'], 'regulatory')
on conflict (term_vi) do nothing;

grant select on public.gmp_glossary to authenticated, service_role;

-- (2) Multi-Query RRF tầng-2 ----------------------------------------------
create or replace function public.hybrid_search_multi_v1(
  p_embeddings text[],
  p_fts_queries text[],
  p_match_threshold double precision default 0.4,
  p_match_count integer default 8,
  p_user_id uuid default null,
  p_language_preference text default 'any',
  p_source_category text default 'any',
  p_document_type text default null,
  p_max_trust_level integer default 5,
  p_equipment_type text default null,
  p_min_quality numeric default 0.3,
  p_rrf_k integer default 60,
  p_pool_size integer default 30
)
returns table(
  chunk_id uuid, document_id uuid, content text, document_code text, document_title text,
  document_version text, language_code public.language_code, source_type public.source_type,
  source_category text, source_organization text, trust_level integer, is_summary boolean,
  page_number integer, section_code text, section_title text, effective_date date,
  next_review_date date, lifecycle_state text, quality_score numeric,
  similarity_score double precision, fts_score double precision, combined_score double precision,
  fused_rrf double precision, variant_hits integer
)
language sql stable security definer set search_path = public, extensions
as $$
  with variants as (
    select e.ord, e.emb, coalesce(q.fts, '') as fts
    from unnest(p_embeddings) with ordinality as e(emb, ord)
    left join unnest(p_fts_queries) with ordinality as q(fts, ord2) on q.ord2 = e.ord
  ),
  hits as (
    select v.ord, h.*,
           row_number() over (partition by v.ord order by h.combined_score desc, h.chunk_id) as rnk
    from variants v
    cross join lateral public.hybrid_search_v4(
      v.emb::extensions.vector, v.fts, p_match_threshold, p_pool_size, p_user_id,
      p_language_preference, p_source_category, p_document_type, p_max_trust_level,
      p_equipment_type, p_min_quality, p_rrf_k, p_pool_size
    ) h
  ),
  fused as (
    select chunk_id, sum(1.0 / (p_rrf_k + rnk)) as fused_rrf, count(*)::int as variant_hits
    from hits group by chunk_id
  ),
  ranked as (
    select h.*, f.fused_rrf, f.variant_hits,
           row_number() over (partition by h.chunk_id order by h.rnk) as pick
    from hits h join fused f on f.chunk_id = h.chunk_id
  )
  select chunk_id, document_id, content, document_code, document_title, document_version,
         language_code, source_type, source_category, source_organization, trust_level,
         is_summary, page_number, section_code, section_title, effective_date,
         next_review_date, lifecycle_state, quality_score, similarity_score, fts_score,
         combined_score, fused_rrf, variant_hits
  from ranked
  where pick = 1
  order by fused_rrf desc, combined_score desc, chunk_id
  limit p_match_count;
$$;

comment on function public.hybrid_search_multi_v1 is
  'CRAVE-044: Multi-Query song song + RRF tầng-2. Chạy hybrid_search_v4 cho N biến thể (embeddings[]/fts_queries[]) rồi hợp nhất bằng RRF 1/(k+rank). variant_hits = số biến thể tìm thấy chunk (đồng thuận). Fail-closed kế thừa từ v4.';

revoke all on function public.hybrid_search_multi_v1(text[], text[], double precision, integer, uuid, text, text, text, integer, text, numeric, integer, integer) from public, anon;
grant execute on function public.hybrid_search_multi_v1(text[], text[], double precision, integer, uuid, text, text, text, integer, text, numeric, integer, integer) to authenticated, service_role;

commit;
