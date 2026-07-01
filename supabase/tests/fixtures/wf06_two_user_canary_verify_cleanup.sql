-- R01-A08 cleanup verification. Read-only transaction.
begin;

do $verify$
declare
  auth_count bigint;
  profile_count bigint;
  access_count bigint;
begin
  select count(*) into auth_count
  from auth.users
  where lower(email) in (
    'crave-wf06-canary-a@invalid.example',
    'crave-wf06-canary-b@invalid.example'
  );

  select count(*) into profile_count
  from public.user_profiles
  where employee_code in ('CRAVE-WF06-A','CRAVE-WF06-B')
    or lower(email) in (
      'crave-wf06-canary-a@invalid.example',
      'crave-wf06-canary-b@invalid.example'
    );

  select count(*) into access_count
  from public.document_access da
  join public.documents d on d.id=da.document_id
  where d.document_code in ('GMP-SOP-001','GMP-SOP-002')
    and da.user_id in (
      select id from public.user_profiles
      where employee_code in ('CRAVE-WF06-A','CRAVE-WF06-B')
    );

  if auth_count <> 0 or profile_count <> 0 or access_count <> 0 then
    raise exception 'R01-A08 cleanup verify fail auth=% profiles=% access=%.',
      auth_count, profile_count, access_count;
  end if;
end
$verify$;

rollback;
