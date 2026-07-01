-- Migration 031: hybrid_search_v4 — Reciprocal Rank Fusion (RRF) hybrid retrieval.
-- Additive: KHÔNG thay hybrid_search_v3 (v3 giữ nguyên cho WF-02 hiện tại).
-- Giữ NGUYÊN cổng fail-closed version/chunk của 029 (embedding không làm corpus
-- chưa duyệt tìm được). Khác v3: thay weighted-sum bằng 2 pool độc lập (FTS + vector)
-- hợp nhất bằng RRF 1/(k+rank), k=60, cộng metadata boost nhỏ để tie-break.

begin;

create or replace function public.hybrid_search_v4(
  p_query_embedding extensions.vector,
  p_query_text text default '',
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
  chunk_id uuid,
  document_id uuid,
  content text,
  document_code text,
  document_title text,
  document_version text,
  language_code public.language_code,
  source_type public.source_type,
  source_category text,
  source_organization text,
  trust_level integer,
  is_summary boolean,
  page_number integer,
  section_code text,
  section_title text,
  effective_date date,
  next_review_date date,
  lifecycle_state text,
  quality_score numeric,
  similarity_score double precision,
  fts_score double precision,
  combined_score double precision
)
language plpgsql
stable
security definer
set search_path to 'pg_catalog', 'public', 'extensions'
as $function$
declare
  v_tsquery tsquery;
begin
  if p_query_text is not null and trim(p_query_text) <> '' then
    v_tsquery := websearch_to_tsquery('simple', p_query_text);
  else
    v_tsquery := null;
  end if;

  return query
  with gated as (
    -- Tập ứng viên đã qua cổng fail-closed (giống hệt 029), KHÔNG order/limit ở đây.
    select
      dc.id as chunk_id,
      dc.document_id,
      dc.content,
      dc.document_code,
      d.document_title,
      dc.document_version,
      dc.language_code,
      dc.source_type,
      coalesce(dc.source_category, d.source_category, 'internal') as source_category,
      coalesce(dc.source_organization, d.source_organization) as source_organization,
      coalesce(dc.trust_level, d.trust_level, 3) as trust_level,
      coalesce(dc.is_summary, d.is_summary, false) as is_summary,
      dc.page_number,
      dc.section_code,
      dc.section_title,
      d.effective_date,
      d.next_review_date,
      public.get_lifecycle_state(
        d.status, d.approved_for_ai_use, d.effective_date,
        d.next_review_date, d.superseded_at, d.retired_date
      ) as lifecycle_state,
      coalesce(dc.quality_score, 1.0) as quality_score,
      (1 - (dc.embedding <=> p_query_embedding)) as sim_score,
      case
        when v_tsquery is null then 0.0
        else least(ts_rank(dc.content_tsv, v_tsquery) * 10.0, 1.0)
      end as fts_raw
    from public.document_chunks dc
    join public.documents d
      on d.id = dc.document_id
    join public.document_versions dv
      on dv.id = d.current_version_id
     and dv.document_id = d.id
     and dv.version_label = dc.document_version
    where
      dv.approved_for_ai_use = true
      and dv.approval_evidence_status = 'verified'
      and dv.hash_status = 'verified'
      and dv.license_status in ('allowed', 'curated')
      and dv.parse_status in ('success', 'partial')
      and dv.binary_sha256 is not null
      and dv.content_sha256 is not null
      and dv.parse_quality_score is not null
      and dv.parsed_at is not null
      and dv.retired_at is null
      and dc.status = 'approved_for_ai_use'::public.document_status
      and dc.embedding is not null
      and public.document_is_currently_valid(
        d.status, d.approved_for_ai_use, d.effective_date,
        d.superseded_at, d.retired_date
      )
      and not (d.is_ai_translated = true and d.translation_status = 'ai_translation_draft')
      and coalesce(dc.quality_score, 1.0) >= p_min_quality
      and (
        p_language_preference = 'any'
        or dc.language_code::text = p_language_preference
        or (p_language_preference = 'vi' and dc.language_code = 'en')
      )
      and (
        p_source_category = 'any'
        or coalesce(dc.source_category, d.source_category, 'internal') = p_source_category
      )
      and coalesce(dc.trust_level, d.trust_level, 3) <= p_max_trust_level
      and (p_document_type is null or d.document_type::text = p_document_type)
      and (p_equipment_type is null or d.equipment_type = p_equipment_type)
      and (
        (1 - (dc.embedding <=> p_query_embedding)) >= p_match_threshold
        or (v_tsquery is not null and dc.content_tsv @@ v_tsquery)
      )
  ),
  -- Pool 1: FTS (chỉ chunk khớp từ khóa), xếp hạng theo ts_rank.
  fts_pool as (
    select g.chunk_id,
           row_number() over (order by g.fts_raw desc, g.chunk_id) as fts_rank
    from gated g
    where g.fts_raw > 0
    order by g.fts_raw desc
    limit p_pool_size
  ),
  -- Pool 2: Vector (chỉ chunk đạt ngưỡng cosine), xếp hạng theo similarity.
  vec_pool as (
    select g.chunk_id,
           row_number() over (order by g.sim_score desc, g.chunk_id) as vec_rank
    from gated g
    where g.sim_score >= p_match_threshold
    order by g.sim_score desc
    limit p_pool_size
  ),
  fused as (
    select
      g.*,
      f.fts_rank,
      v.vec_rank,
      coalesce(1.0 / (p_rrf_k + f.fts_rank), 0.0)
        + coalesce(1.0 / (p_rrf_k + v.vec_rank), 0.0) as rrf_score
    from gated g
    left join fts_pool f on f.chunk_id = g.chunk_id
    left join vec_pool v on v.chunk_id = g.chunk_id
    where f.chunk_id is not null or v.chunk_id is not null
  )
  select
    fu.chunk_id,
    fu.document_id,
    fu.content,
    fu.document_code,
    fu.document_title,
    fu.document_version,
    fu.language_code,
    fu.source_type,
    fu.source_category,
    fu.source_organization,
    fu.trust_level,
    fu.is_summary,
    fu.page_number,
    fu.section_code,
    fu.section_title,
    fu.effective_date,
    fu.next_review_date,
    fu.lifecycle_state,
    fu.quality_score,
    fu.sim_score as similarity_score,
    fu.fts_raw as fts_score,
    -- RRF là thành phần chính; boost metadata nhỏ để tie-break (không lấn át RRF).
    fu.rrf_score
      + (case when p_query_text <> '' and fu.document_code ilike '%' || p_query_text || '%' then 0.010 else 0 end)
      + ((6 - least(fu.trust_level, 5))::float / 5.0 * 0.005)
      + (case when p_language_preference <> 'any' and fu.language_code::text = p_language_preference then 0.005 else 0 end)
      + (fu.quality_score::float * 0.002)
      - (case when fu.is_summary then 0.005 else 0 end)
      as combined_score
  from fused fu
  order by combined_score desc
  limit p_match_count;
end;
$function$;

comment on function public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
) is 'CRAVE-031: hybrid retrieval V4 — 2 pool độc lập (FTS + vector) hợp nhất bằng RRF 1/(k+rank), k=60, + metadata boost nhỏ. Giữ nguyên cổng fail-closed version/chunk của 029. Additive, không thay v3.';

-- Grant khớp v3 (030d): authenticated được execute; anon KHÔNG; service_role giữ.
revoke all on function public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
) from public;
grant execute on function public.hybrid_search_v4(
  extensions.vector, text, double precision, integer, uuid, text, text, text,
  integer, text, numeric, integer, integer
) to authenticated, service_role;

commit;
