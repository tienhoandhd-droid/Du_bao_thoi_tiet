-- CRAVE rollback: 20260701150000_034_crave_moa_prompts_down
-- Gỡ 2 prompt MoA (CRAVE-034) khỏi prompt_versions. Chỉ chạy khi có approval.

begin;

delete from public.prompt_versions
where version = 'v1.0'
  and prompt_name in ('crave_moa_proposer', 'crave_moa_aggregator');

commit;
