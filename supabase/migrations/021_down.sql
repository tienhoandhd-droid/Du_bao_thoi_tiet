-- Rollback migration 021 (bao gồm 021b/c/d):
-- Khôi phục cột score về numeric(5,4) (021d rollback)
ALTER TABLE eval_runs
  ALTER COLUMN score_mean TYPE numeric(5,4),
  ALTER COLUMN score_min  TYPE numeric(5,4);

-- Xóa hàm eval (021c/b rollback)
DROP FUNCTION IF EXISTS run_fts_eval_v1(integer, text, text);

-- Xóa RLS policies (021 rollback)
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'eval_results_admin_all' AND tablename = 'eval_results') THEN
    DROP POLICY eval_results_admin_all ON eval_results;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'eval_runs_admin_all' AND tablename = 'eval_runs') THEN
    DROP POLICY eval_runs_admin_all ON eval_runs;
  END IF;
END $$;
