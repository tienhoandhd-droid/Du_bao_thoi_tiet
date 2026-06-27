-- CRAVE Chat 15 - Rollback Migration 018.
-- Chi xoa cac dong seed dung khoa nghiep vu va phien ban cua migration 018.

begin;

delete from public.equipment_registry
where equipment_code in ('HPLC-001', 'BALANCE-001');

delete from public.calculation_formulas
where formula_code in ('rsd_repeatability', 'recovery_rate', 'lod_lod_calc')
  and version = '1.0';

delete from public.validation_templates
where protocol_type in ('iq', 'oq', 'pq')
  and language_code = 'vi'
  and version = '1.0';

delete from public.prompt_versions
where prompt_name in ('protocol_writer', 'protocol_checker', 'calculation_reviewer')
  and version = 'v1.0';

commit;
