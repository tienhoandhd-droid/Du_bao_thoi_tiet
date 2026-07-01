-- Migration 021b: Eval function v2 — content-keyword matching thay vì document_code matching
-- expected_sources của golden_questions là keyword GMP (CAPA, sai lệch...) không phải chỉ mã tài liệu.
-- Xem 021c cho phiên bản cuối (v3 OR-tsquery).
CREATE OR REPLACE FUNCTION run_fts_eval_v1(
  p_top_k        integer  DEFAULT 5,
  p_model_tag    text     DEFAULT 'fts-v1',
  p_notes        text     DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Placeholder: superseded by 021c (v3 OR-tsquery)
  RAISE EXCEPTION 'run_fts_eval_v1 v2 is superseded by v3 in migration 021c. Should not be reached.';
END;
$$;

GRANT EXECUTE ON FUNCTION run_fts_eval_v1(integer, text, text) TO authenticated;
