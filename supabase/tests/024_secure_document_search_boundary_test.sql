-- CRAVE R01 / Static + catalog contract checks cho migration 024.
-- Chạy trên clone/test database sau khi apply 024; không dùng script này để apply live.

begin;

do $$
declare
  function_oid regprocedure := to_regprocedure(
    'public.search_documents_v1(text,public.document_type,public.source_type,public.language_code,public.document_status,text,text,text,public.translation_status,boolean,integer,integer)'
  );
  function_definition text;
  function_config text[];
begin
  if function_oid is null then
    raise exception 'TEST-024: thiếu exact RPC signature search_documents_v1.';
  end if;

  select pg_get_functiondef(p.oid), p.proconfig
  into function_definition, function_config
  from pg_proc p
  where p.oid = function_oid::oid
    and p.prosecdef = false
    and p.provolatile = 's'
    and p.prorettype = 'jsonb'::regtype;

  if function_definition is null then
    raise exception 'TEST-024: function phải SECURITY INVOKER, STABLE và trả jsonb.';
  end if;

  if function_config is null
    or not ('search_path=pg_catalog, public' = any(function_config))
  then
    raise exception 'TEST-024: search_path chưa khóa đúng pg_catalog, public.';
  end if;

  if function_definition !~ 'auth[.]uid[(][)]'
    or function_definition !~ 'public[.]documents'
    or function_definition !~ 'user_has_any_role'
  then
    raise exception 'TEST-024: thiếu JWT/RLS source/role guard trong definition.';
  end if;

  if function_definition ~* '\mexecute\M|\mformat\s*\('
  then
    raise exception 'TEST-024: không cho dynamic SQL trong search_documents_v1.';
  end if;

  if exists (
    select 1
    from pg_proc p
    cross join lateral aclexplode(
      coalesce(p.proacl, acldefault('f', p.proowner))
    ) privilege
    where p.oid = function_oid::oid
      and privilege.grantee = 0
      and privilege.privilege_type = 'EXECUTE'
  )
    or has_function_privilege('anon', function_oid, 'EXECUTE')
    or has_function_privilege('service_role', function_oid, 'EXECUTE')
  then
    raise exception 'TEST-024: PUBLIC/anon/service_role không được EXECUTE RPC user-facing.';
  end if;

  if not has_function_privilege('authenticated', function_oid, 'EXECUTE') then
    raise exception 'TEST-024: authenticated phải được EXECUTE RPC.';
  end if;

  if not exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'documents'
      and c.relrowsecurity
  ) then
    raise exception 'TEST-024: documents phải bật RLS.';
  end if;
end
$$;

rollback;
