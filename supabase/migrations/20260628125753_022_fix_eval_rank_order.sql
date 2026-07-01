-- Migration 022: Sửa thứ tự xếp hạng của run_fts_eval_v1.
-- Bug fix: thứ tự kết quả cuối đổi từ ORDER BY document_code sang
-- ORDER BY rank DESC; DISTINCT ON theo tài liệu vẫn giữ nguyên.
CREATE OR REPLACE FUNCTION public.run_fts_eval_v1(
  p_top_k integer DEFAULT 5,
  p_model_tag text DEFAULT 'fts-v3',
  p_notes text DEFAULT NULL
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, extensions
AS $function$
DECLARE
  q           RECORD;
  chunk_rec   RECORD;
  hit_pos     integer;
  rr          numeric;
  chunk_idx   integer;
  results_arr jsonb := '[]'::jsonb;
  run_id      uuid;
  n_total     integer := 0;
  n_with_src  integer := 0;
  hit1 integer := 0; hit3 integer := 0; hit5 integer := 0;
  mrr_sum     numeric := 0;
  hit_at_1_pct numeric(5,2); hit_at_3_pct numeric(5,2);
  hit_at_5_pct numeric(5,2); mrr_val numeric(6,4);
  pass_flag boolean; chunk_hit boolean; kw text;
  q_tsv tsvector; q_lexemes text[]; q_tsquery tsquery;
BEGIN
  SELECT COUNT(*) INTO n_total FROM golden_questions WHERE is_active = true;
  FOR q IN
    SELECT id, question_text, expected_sources FROM golden_questions
    WHERE is_active = true AND expected_sources IS NOT NULL
      AND array_length(expected_sources, 1) > 0
  LOOP
    n_with_src := n_with_src + 1;
    hit_pos := NULL; rr := 0; chunk_idx := 0;
    q_tsv := to_tsvector('simple', q.question_text);
    q_lexemes := ARRAY(SELECT lexeme FROM unnest(q_tsv) ORDER BY lexeme);
    IF array_length(q_lexemes, 1) IS NULL OR array_length(q_lexemes, 1) = 0 THEN
      CONTINUE;
    END IF;
    q_tsquery := to_tsquery('simple', array_to_string(q_lexemes, ' | '));
    -- FIX v2: DISTINCT ON per document, then rank by relevance DESC (not alphabetical)
    FOR chunk_rec IN
      SELECT document_code, content, rank FROM (
        SELECT DISTINCT ON (dc2.document_code)
               dc2.document_code, dc2.content,
               ts_rank(dc2.content_tsv, q_tsquery) AS rank
        FROM   document_chunks dc2
        JOIN   documents d ON d.id = dc2.document_id
        WHERE  dc2.content_tsv @@ q_tsquery
          AND  document_is_currently_valid(
                 d.status, d.approved_for_ai_use,
                 d.effective_date, d.superseded_at, d.retired_date)
        ORDER BY dc2.document_code, rank DESC
      ) sub
      ORDER BY rank DESC LIMIT p_top_k
    LOOP
      chunk_idx := chunk_idx + 1; chunk_hit := false;
      FOREACH kw IN ARRAY q.expected_sources LOOP
        IF chunk_hit THEN EXIT; END IF;
        IF chunk_rec.document_code ILIKE kw THEN chunk_hit := true;
        ELSIF length(kw) >= 3 AND chunk_rec.content ILIKE '%' || kw || '%' THEN
          chunk_hit := true;
        END IF;
      END LOOP;
      IF chunk_hit AND hit_pos IS NULL THEN
        hit_pos := chunk_idx; rr := 1.0 / chunk_idx;
      END IF;
    END LOOP;
    IF hit_pos IS NOT NULL THEN
      IF hit_pos <= 1 THEN hit1 := hit1 + 1; END IF;
      IF hit_pos <= 3 THEN hit3 := hit3 + 1; END IF;
      IF hit_pos <= 5 THEN hit5 := hit5 + 1; END IF;
      mrr_sum := mrr_sum + rr;
    END IF;
    results_arr := results_arr || jsonb_build_array(jsonb_build_object(
      'question_id', q.id, 'question_text', q.question_text,
      'expected_sources', q.expected_sources,
      'hit_position', hit_pos, 'rr', rr,
      'passed', (hit_pos IS NOT NULL AND hit_pos <= p_top_k)
    ));
  END LOOP;
  hit_at_1_pct := ROUND(hit1*100.0/NULLIF(n_with_src,0),2);
  hit_at_3_pct := ROUND(hit3*100.0/NULLIF(n_with_src,0),2);
  hit_at_5_pct := ROUND(hit5*100.0/NULLIF(n_with_src,0),2);
  mrr_val      := ROUND(mrr_sum/NULLIF(n_with_src,0),4);
  pass_flag    := (hit_at_5_pct IS NOT NULL AND hit_at_5_pct >= 80);
  INSERT INTO eval_runs (model_tag, n_questions, score_mean, score_min, passed, notes)
  VALUES (p_model_tag, n_with_src, hit_at_5_pct, hit_at_1_pct, pass_flag,
    COALESCE(p_notes, 'FTS OR-tsquery eval v3 rank-fixed — Hit@' || p_top_k::text
      || ' threshold 80%. ' || n_with_src::text||'/'||n_total::text||' câu có nguồn.'))
  RETURNING id INTO run_id;
  INSERT INTO eval_results (run_id, question_id, score_faithfulness, score_relevancy, passed, raw_json)
  SELECT run_id, (r->>'question_id')::uuid, (r->>'rr')::numeric,
         CASE WHEN (r->>'hit_position') IS NOT NULL THEN 1.0 ELSE 0.0 END,
         (r->>'passed')::boolean, r
  FROM jsonb_array_elements(results_arr) AS r;
  RETURN jsonb_build_object(
    'run_id', run_id, 'model_tag', p_model_tag,
    'n_total', n_total, 'n_with_sources', n_with_src,
    'hit_at_1_pct', hit_at_1_pct, 'hit_at_3_pct', hit_at_3_pct,
    'hit_at_5_pct', hit_at_5_pct, 'mrr', mrr_val,
    'passed', pass_flag, 'threshold_pct', 80
  );
END;
$function$;
