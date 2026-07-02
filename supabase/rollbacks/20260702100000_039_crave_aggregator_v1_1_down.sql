-- Rollback CRAVE-039: trả active về v1.0, gỡ v1.1.
begin;
update public.prompt_versions set is_active = true
 where prompt_name = 'crave_moa_aggregator' and version = 'v1.0';
delete from public.prompt_versions
 where prompt_name = 'crave_moa_aggregator' and version = 'v1.1';
commit;
