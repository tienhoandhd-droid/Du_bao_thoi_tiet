-- CRAVE rollback: 20260701133000_033_crave_prompts_seed_down
-- Gỡ 4 prompt CRAVE (CRAVE-033) khỏi prompt_versions. Chỉ chạy khi có approval.

begin;

delete from public.prompt_versions
where version = 'v1.0'
  and prompt_name in (
    'crave_claim_framing',
    'crave_support_agent',
    'crave_refute_agent',
    'crave_judge'
  );

commit;
