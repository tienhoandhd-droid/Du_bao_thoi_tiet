-- R01-A08 live fixture setup. Chỉ chạy qua operator sau exact approval.
begin;

do $preflight$
declare
  auth_count bigint;
  profile_count bigint;
  existing_access bigint;
  marker_docs bigint;
begin
  select count(*) into auth_count
  from auth.users
  where lower(email) in (
    'crave-wf06-canary-a@invalid.example',
    'crave-wf06-canary-b@invalid.example'
  )
    and raw_user_meta_data->>'crave_canary' = 'wf06_rls_v1';

  select count(*) into profile_count
  from public.user_profiles
  where lower(email) in (
    'crave-wf06-canary-a@invalid.example',
    'crave-wf06-canary-b@invalid.example'
  );

  select count(*) into existing_access
  from public.document_access da
  join public.documents d on d.id=da.document_id
  where d.document_code in ('GMP-SOP-001','GMP-SOP-002') and da.is_active;

  select count(*) into marker_docs
  from public.documents
  where document_code in ('GMP-SOP-001','GMP-SOP-002')
    and access_level='internal'
    and source_type::text='internal_sop'
    and approved_for_ai_use;

  if auth_count <> 2 or profile_count <> 0 or existing_access <> 0 or marker_docs <> 2 then
    raise exception
      'R01-A08 setup preflight fail auth=% profiles=% existing_access=% marker_docs=%.',
      auth_count, profile_count, existing_access, marker_docs;
  end if;
end
$preflight$;

insert into public.user_profiles (
  id, full_name, email, department, position, employee_code,
  is_active, preferred_language
)
select
  u.id,
  case lower(u.email)
    when 'crave-wf06-canary-a@invalid.example' then 'CRAVE WF06 Canary A'
    else 'CRAVE WF06 Canary B'
  end,
  lower(u.email),
  case lower(u.email)
    when 'crave-wf06-canary-a@invalid.example' then 'CRAVE_CANARY_A'
    else 'CRAVE_CANARY_B'
  end,
  'RLS test identity',
  case lower(u.email)
    when 'crave-wf06-canary-a@invalid.example' then 'CRAVE-WF06-A'
    else 'CRAVE-WF06-B'
  end,
  true,
  'vi'::public.language_code
from auth.users u
where lower(u.email) in (
  'crave-wf06-canary-a@invalid.example',
  'crave-wf06-canary-b@invalid.example'
)
  and u.raw_user_meta_data->>'crave_canary'='wf06_rls_v1';

insert into public.document_access (
  document_id, user_id, can_view, can_edit, can_approve,
  granted_by, granted_at, expires_at, is_active
)
select
  d.id,
  p.id,
  true,
  false,
  false,
  null,
  now(),
  now() + interval '2 hours',
  true
from public.user_profiles p
join public.documents d
  on d.document_code = case p.employee_code
    when 'CRAVE-WF06-A' then 'GMP-SOP-001'
    when 'CRAVE-WF06-B' then 'GMP-SOP-002'
  end
where p.employee_code in ('CRAVE-WF06-A','CRAVE-WF06-B');

do $verify$
declare
  profiles bigint;
  grants bigint;
begin
  select count(*) into profiles
  from public.user_profiles
  where employee_code in ('CRAVE-WF06-A','CRAVE-WF06-B');

  select count(*) into grants
  from public.document_access da
  join public.user_profiles p on p.id=da.user_id
  join public.documents d on d.id=da.document_id
  where da.is_active and da.can_view and not da.can_edit and not da.can_approve
    and (
      (p.employee_code='CRAVE-WF06-A' and d.document_code='GMP-SOP-001')
      or (p.employee_code='CRAVE-WF06-B' and d.document_code='GMP-SOP-002')
    );

  if profiles <> 2 or grants <> 2 then
    raise exception 'R01-A08 setup verify fail profiles=% grants=%.', profiles, grants;
  end if;
end
$verify$;

commit;
