-- CRAVE-028 post-apply read-only ACL test.
begin;

do $test$
begin
  if to_regclass('public.document_versions') is null then
    raise exception 'CRAVE-028 test: thiếu document_versions.';
  end if;

  if has_table_privilege('anon','public.document_versions','SELECT')
    or not has_table_privilege('authenticated','public.document_versions','SELECT')
    or not has_table_privilege('authenticated','public.document_versions','INSERT')
    or not has_table_privilege('authenticated','public.document_versions','UPDATE')
    or has_table_privilege('authenticated','public.document_versions','DELETE')
    or has_table_privilege('authenticated','public.document_versions','TRUNCATE')
    or has_table_privilege('authenticated','public.document_versions','REFERENCES')
    or has_table_privilege('authenticated','public.document_versions','TRIGGER')
    or not has_table_privilege('service_role','public.document_versions','SELECT')
    or not has_table_privilege('service_role','public.document_versions','INSERT')
    or not has_table_privilege('service_role','public.document_versions','UPDATE')
    or has_table_privilege('service_role','public.document_versions','DELETE')
    or has_table_privilege('service_role','public.document_versions','TRUNCATE')
    or has_table_privilege('service_role','public.document_versions','REFERENCES')
    or has_table_privilege('service_role','public.document_versions','TRIGGER')
  then
    raise exception 'CRAVE-028 test: ACL least privilege sai.';
  end if;
end
$test$;

rollback;
