-- Migration 021d: Mở rộng precision cột score trong eval_runs
-- eval_runs.score_mean/score_min lưu phần trăm 0-100 nhưng numeric(5,4) chỉ chứa được tới 9.9999.
-- Đổi sang numeric(5,2) để chứa giá trị phần trăm đến 99.99%.
ALTER TABLE eval_runs
  ALTER COLUMN score_mean TYPE numeric(5,2),
  ALTER COLUMN score_min  TYPE numeric(5,2);
