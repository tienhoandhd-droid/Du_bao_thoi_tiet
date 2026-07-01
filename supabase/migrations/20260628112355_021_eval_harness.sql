-- Migration 021: Eval Harness — RLS policies + FTS retrieval eval function
-- Idempotent: DO-block guards for policies; CREATE OR REPLACE for function.

-- ── 1. RLS POLICIES ──────────────────────────────────────────────────────────

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE policyname = 'eval_runs_admin_all' AND tablename = 'eval_runs'
  ) THEN
    CREATE POLICY eval_runs_admin_all ON eval_runs FOR ALL
      USING (user_has_any_role(ARRAY['admin'::user_role_name, 'qa_manager'::user_role_name]));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE policyname = 'eval_results_admin_all' AND tablename = 'eval_results'
  ) THEN
    CREATE POLICY eval_results_admin_all ON eval_results FOR ALL
      USING (user_has_any_role(ARRAY['admin'::user_role_name, 'qa_manager'::user_role_name]));
  END IF;
END $$;

-- ── 2. EVAL FUNCTION ─────────────────────────────────────────────────────────
-- Chạy FTS retrieval eval trên toàn bộ golden_questions có expected_sources.
-- Không cần embedding — dùng content_tsv (BM25 component của hybrid_search_v3).
-- Metrics: Hit@1, Hit@3, Hit@5, MRR.
-- Ghi kết quả vào eval_runs + eval_results; trả về summary jsonb.

CREATE OR REPLACE FUNCTION run_fts_eval_v1(
  p_top_k        integer  DEFAULT 5,
  p_model_tag    text     DEFAULT 'fts-v1',
  p_notes        text     DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER  -- bypass RLS để đọc golden_questions + document_chunks
SET search_path = public
AS $$
DECLARE
  q          RECORD;
  top_docs   text[];
  hit_pos    integer;
  rr         numeric;

  results_arr jsonb := '[]'::jsonb;
  run_id      uuid;

  n_total     integer := 0;
  n_with_src  integer := 0;
  hit1        integer := 0;
  hit3        integer := 0;
  hit5        integer := 0;
  mrr_sum     numeric := 0;

  hit_at_1_pct  numeric(5,2);
  hit_at_3_pct  numeric(5,2);
  hit_at_5_pct  numeric(5,2);
  mrr_val       numeric(6,4);
  pass_flag     boolean;
BEGIN
  -- Count total active questions
  SELECT COUNT(*) INTO n_total FROM golden_questions WHERE is_active = true;

  -- Loop over questions that have expected_sources
  FOR q IN
    SELECT id, question_text, expected_sources
    FROM   golden_questions
    WHERE  is_active = true
      AND  expected_sources IS NOT NULL
      AND  array_length(expected_sources, 1) > 0
  LOOP
    n_with_src := n_with_src + 1;

    -- FTS search against document_chunks using content_tsv index
    SELECT array_agg(dc.document_code ORDER BY rank DESC)
    INTO   top_docs
    FROM (
      SELECT DISTINCT ON (dc2.document_code)
             dc2.document_code,
             ts_rank(dc2.content_tsv, websearch_to_tsquery('simple', q.question_text)) AS rank
      FROM   document_chunks dc2
      JOIN   documents d ON d.id = dc2.document_id
      WHERE  dc2.content_tsv @@ websearch_to_tsquery('simple', q.question_text)
        AND  document_is_currently_valid(
               d.status, d.approved_for_ai_use,
               d.effective_date, d.superseded_at, d.retired_date)
      ORDER  BY dc2.document_code, rank DESC
      LIMIT  p_top_k
    ) dc;

    -- Find first hit position among expected sources
    hit_pos := NULL;
    rr       := 0;
    IF top_docs IS NOT NULL AND array_length(top_docs, 1) > 0 THEN
      FOR i IN 1 .. array_length(top_docs, 1) LOOP
        IF top_docs[i] = ANY(q.expected_sources) AND hit_pos IS NULL THEN
          hit_pos := i;
          rr := 1.0 / i;
        END IF;
      END LOOP;
    END IF;

    -- Accumulate metrics
    IF hit_pos IS NOT NULL THEN
      IF hit_pos <= 1 THEN hit1 := hit1 + 1; END IF;
      IF hit_pos <= 3 THEN hit3 := hit3 + 1; END IF;
      IF hit_pos <= 5 THEN hit5 := hit5 + 1; END IF;
      mrr_sum := mrr_sum + rr;
    END IF;

    -- Append per-question detail
    results_arr := results_arr || jsonb_build_array(jsonb_build_object(
      'question_id',      q.id,
      'question_text',    q.question_text,
      'expected_sources', q.expected_sources,
      'retrieved_docs',   COALESCE(top_docs, '{}'),
      'hit_position',     hit_pos,
      'rr',               rr,
      'passed',           (hit_pos IS NOT NULL AND hit_pos <= p_top_k)
    ));
  END LOOP;

  -- Compute aggregates
  hit_at_1_pct := ROUND(hit1 * 100.0 / NULLIF(n_with_src, 0), 2);
  hit_at_3_pct := ROUND(hit3 * 100.0 / NULLIF(n_with_src, 0), 2);
  hit_at_5_pct := ROUND(hit5 * 100.0 / NULLIF(n_with_src, 0), 2);
  mrr_val      := ROUND(mrr_sum / NULLIF(n_with_src, 0), 4);
  -- Pass threshold: hit@5 >= 80% (aligns with whitepaper faithfulness gate)
  pass_flag    := (hit_at_5_pct IS NOT NULL AND hit_at_5_pct >= 80);

  -- Write to eval_runs
  INSERT INTO eval_runs (model_tag, n_questions, score_mean, score_min, passed, notes)
  VALUES (
    p_model_tag,
    n_with_src,
    hit_at_5_pct,          -- score_mean = Hit@5% (primary metric for this eval type)
    hit_at_1_pct,          -- score_min  = Hit@1% (strictest metric)
    pass_flag,
    COALESCE(p_notes, 'FTS retrieval eval — hit@' || p_top_k::text
             || ' threshold 80%. Questions with sources: ' || n_with_src::text
             || '/' || n_total::text)
  )
  RETURNING id INTO run_id;

  -- Write per-question results to eval_results
  INSERT INTO eval_results (run_id, question_id, score_faithfulness, score_relevancy, passed, raw_json)
  SELECT
    run_id,
    (r->>'question_id')::uuid,
    (r->>'rr')::numeric,              -- rr ≈ faithfulness proxy (1/rank)
    CASE WHEN (r->>'hit_position') IS NOT NULL THEN 1.0 ELSE 0.0 END,
    (r->>'passed')::boolean,
    r
  FROM jsonb_array_elements(results_arr) AS r;

  -- Return summary
  RETURN jsonb_build_object(
    'run_id',           run_id,
    'model_tag',        p_model_tag,
    'n_total',          n_total,
    'n_with_sources',   n_with_src,
    'hit_at_1_pct',     hit_at_1_pct,
    'hit_at_3_pct',     hit_at_3_pct,
    'hit_at_5_pct',     hit_at_5_pct,
    'mrr',              mrr_val,
    'passed',           pass_flag,
    'threshold_pct',    80
  );
END;
$$;

-- Allow authenticated users (admin/qa_manager via RLS) to call from frontend
GRANT EXECUTE ON FUNCTION run_fts_eval_v1(integer, text, text) TO authenticated;
