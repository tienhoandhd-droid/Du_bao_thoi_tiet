-- Migration 029: Harden hybrid_search_v3 with immutable document version gate.
-- CRAVE P0 safety: embeddings must not make legacy/unverified corpus searchable.

begin;

create or replace function public.hybrid_search_v3(
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
  p_min_quality numeric default 0.3
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
  with candidates as (
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
        d.status,
        d.approved_for_ai_use,
        d.effective_date,
        d.next_review_date,
        d.superseded_at,
        d.retired_date
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
      -- CRAVE-029 fail-closed version evidence gate:
      -- A chunk is searchable only when the current immutable version itself is
      -- approved for AI use and has verified raw/hash/parse/license evidence.
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
      -- CRAVE-029 chunk gate:
      and dc.status = 'approved_for_ai_use'::public.document_status
      and dc.embedding is not null
      -- Existing document-level governance remains binding.
      and public.document_is_currently_valid(
        d.status,
        d.approved_for_ai_use,
        d.effective_date,
        d.superseded_at,
        d.retired_date
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
    order by (1 - (dc.embedding <=> p_query_embedding)) desc
    limit p_match_count * 3
  )
  select
    c.chunk_id,
    c.document_id,
    c.content,
    c.document_code,
    c.document_title,
    c.document_version,
    c.language_code,
    c.source_type,
    c.source_category,
    c.source_organization,
    c.trust_level,
    c.is_summary,
    c.page_number,
    c.section_code,
    c.section_title,
    c.effective_date,
    c.next_review_date,
    c.lifecycle_state,
    c.quality_score,
    c.sim_score as similarity_score,
    c.fts_raw as fts_score,
    (c.sim_score * 0.55)
      + (c.fts_raw * 0.22)
      + (
        case
          when p_query_text <> '' and c.document_code ilike '%' || p_query_text || '%'
          then 0.05 else 0
        end
      )
      + ((6 - least(c.trust_level, 5))::float / 5.0 * 0.10)
      + (
        case
          when p_language_preference <> 'any'
            and c.language_code::text = p_language_preference
          then 0.06 else 0
        end
      )
      + (c.quality_score::float * 0.02)
      - (case when c.is_summary then 0.05 else 0 end)
      as combined_score
  from candidates c
  order by combined_score desc
  limit p_match_count;
end;
$function$;

comment on function public.hybrid_search_v3(
  extensions.vector,
  text,
  double precision,
  integer,
  uuid,
  text,
  text,
  text,
  integer,
  text,
  numeric
) is 'CRAVE-029: hybrid search fail-closed to current document_versions that have verified raw/hash/parse/license approval evidence before embeddings can affect retrieval.';

commit;
