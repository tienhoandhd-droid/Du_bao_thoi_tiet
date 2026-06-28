-- Rollback migration 021: Eval Harness
DROP FUNCTION IF EXISTS run_fts_eval_v1(integer, text, text);

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'eval_results_admin_all' AND tablename = 'eval_results') THEN
    DROP POLICY eval_results_admin_all ON eval_results;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'eval_runs_admin_all' AND tablename = 'eval_runs') THEN
    DROP POLICY eval_runs_admin_all ON eval_runs;
  END IF;
END $$;
