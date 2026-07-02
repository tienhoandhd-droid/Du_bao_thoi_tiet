-- Rollback CRAVE-038: gỡ hàm flagged_document_codes.
begin;
drop function if exists public.flagged_document_codes();
commit;
