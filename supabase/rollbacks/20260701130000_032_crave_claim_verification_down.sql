-- CRAVE rollback: 20260701130000_032_crave_claim_verification_down
-- Gỡ nền CRAVE Claim Verification (CRAVE-032). Thứ tự đảo phụ thuộc.
-- Lưu ý: append-only guard chặn DELETE/TRUNCATE dữ liệu; DROP TABLE (DDL) vẫn thực thi được.
-- Chỉ chạy khi có change-control/approval; sẽ mất evidence claim/verdict đã ghi.

begin;

-- Append-only guards
drop trigger if exists claim_verdicts_append_only_guard on public.claim_verdicts;
drop trigger if exists claims_append_only_guard on public.claims;

-- Policies
drop policy if exists claim_verdicts_read_own_or_auditor on public.claim_verdicts;
drop policy if exists claims_read_own_or_auditor on public.claims;

-- Index trên ai_query_sources (cột thêm bởi 032)
drop index if exists public.idx_ai_query_sources_stance;

-- Bảng phụ thuộc trước (claim_verdicts -> claims)
drop table if exists public.claim_verdicts;
drop table if exists public.claims;

-- Gỡ cột stance trên ai_query_sources + constraint
alter table public.ai_query_sources
  drop constraint if exists ai_query_sources_stance_strength_check,
  drop constraint if exists ai_query_sources_stance_check;
alter table public.ai_query_sources
  drop column if exists stance_strength,
  drop column if exists stance;

commit;
