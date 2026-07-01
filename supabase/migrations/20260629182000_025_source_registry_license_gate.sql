-- CRAVE deploy migration: 20260629182000_025_source_registry_license_gate
-- Semantic source ID: CRAVE-025 / R02-A01 / UPG-CHAT-03
-- Project bắt buộc: bdttccztjtrcaztjgkot
--
-- Mục tiêu:
--   1. Tạo source_registry canonical và license_rules versioned/append-only.
--   2. Migrate legacy web_sources/approved_sources theo domain, giữ lineage IDs.
--   3. Fail closed: legacy row thiếu approval chỉ metadata_only + inactive.
--   4. Cung cấp typed policy resolver; unknown/inactive/expired luôn deny.
--
-- KHÔNG tự apply. Apply cần dry-run, exact change set và xác nhận riêng.

begin;

do $preflight$
begin
  if to_regclass('public.web_sources') is null
    or to_regclass('public.approved_sources') is null
    or to_regclass('public.user_profiles') is null
  then
    raise exception 'CRAVE-025: thiếu bảng legacy/user_profiles bắt buộc; dừng vì schema drift.';
  end if;

  if to_regprocedure('public.user_has_any_role(public.user_role_name[])') is null then
    raise exception 'CRAVE-025: thiếu user_has_any_role(user_role_name[]).';
  end if;

  if to_regprocedure('public.update_updated_at()') is null then
    raise exception 'CRAVE-025: thiếu update_updated_at().';
  end if;

  if to_regprocedure('public.crave_block_append_only_mutation()') is null then
    raise exception 'CRAVE-025: thiếu crave_block_append_only_mutation().';
  end if;

  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    raise exception 'CRAVE-025: thiếu role authenticated.';
  end if;

  if to_regclass('public.source_registry') is not null
    and coalesce(obj_description(to_regclass('public.source_registry'), 'pg_class'), '')
      not like 'CRAVE-025:%'
  then
    raise exception 'CRAVE-025: source_registry hiện có không mang marker CRAVE-025.';
  end if;

  if to_regclass('public.license_rules') is not null
    and coalesce(obj_description(to_regclass('public.license_rules'), 'pg_class'), '')
      not like 'CRAVE-025:%'
  then
    raise exception 'CRAVE-025: license_rules hiện có không mang marker CRAVE-025.';
  end if;
end
$preflight$;

create table if not exists public.source_registry (
  id uuid primary key default gen_random_uuid(),
  source_name text not null,
  domain text not null,
  organization text not null,
  access_mode text not null default 'deny'
    check (access_mode in ('allow', 'curated', 'metadata_only', 'deny')),
  trust_level integer not null default 3 check (trust_level between 1 and 5),
  public_only boolean not null default true,
  robots_required boolean not null default true,
  crawl_delay_seconds integer not null default 30 check (crawl_delay_seconds between 0 and 86400),
  allowed_content_types text[] not null default '{}',
  seed_urls text[] not null default '{}',
  license_summary text,
  owner_id uuid references public.user_profiles(id),
  approved_by uuid references public.user_profiles(id),
  approved_at timestamptz,
  effective_from timestamptz,
  effective_until timestamptz,
  is_active boolean not null default false,
  legacy_web_source_ids uuid[] not null default '{}',
  legacy_approved_source_ids uuid[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint source_registry_domain_key unique (domain),
  constraint source_registry_domain_format_check check (
    domain = lower(domain)
    and domain !~ '[/?:#@]'
    and domain ~ '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$'
  ),
  constraint source_registry_name_check check (length(btrim(source_name)) between 1 and 200),
  constraint source_registry_organization_check check (length(btrim(organization)) between 1 and 200),
  constraint source_registry_window_check check (
    effective_until is null or effective_from is null or effective_until > effective_from
  ),
  constraint source_registry_approval_check check (
    not is_active
    or (
      approved_by is not null
      and owner_id is not null
      and approved_at is not null
      and effective_from is not null
      and nullif(btrim(license_summary), '') is not null
    )
  )
);

comment on table public.source_registry is
  'CRAVE-025: canonical source/license gate; unknown, inactive hoặc hết hiệu lực phải fail closed.';

create table if not exists public.license_rules (
  id uuid primary key default gen_random_uuid(),
  source_registry_id uuid not null references public.source_registry(id),
  content_pattern text not null,
  decision text not null check (decision in ('allow', 'curated', 'metadata_only', 'deny')),
  reason text not null,
  evidence_url text,
  effective_from timestamptz not null default now(),
  effective_until timestamptz,
  approved_by uuid not null references public.user_profiles(id),
  approved_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint license_rules_pattern_check check (length(btrim(content_pattern)) between 1 and 500),
  constraint license_rules_reason_check check (length(btrim(reason)) between 1 and 2000),
  constraint license_rules_window_check check (
    effective_until is null or effective_until > effective_from
  ),
  constraint license_rules_version_key unique (
    source_registry_id, content_pattern, effective_from
  )
);

comment on table public.license_rules is
  'CRAVE-025: immutable/append-only license decisions; sửa bằng rule mới, không overwrite lịch sử.';

create index if not exists idx_source_registry_active_domain
  on public.source_registry (domain)
  where is_active;
create index if not exists idx_source_registry_mode_effective
  on public.source_registry (access_mode, effective_from, effective_until);
create index if not exists idx_license_rules_source_effective
  on public.license_rules (source_registry_id, effective_from desc, effective_until);

-- Legacy web_sources không có approval evidence trên baseline đã inspect.
-- Không suy diễn is_active=true thành legal allow; migrate fail-closed.
with legacy as (
  select
    regexp_replace(
      lower(split_part(regexp_replace(btrim(w.base_url), '^[a-z][a-z0-9+.-]*://', '', 'i'), '/', 1)),
      '^www\.',
      ''
    ) as domain,
    min(w.organization) as organization,
    min(w.source_name) as source_name,
    greatest(1, least(5, min(coalesce(w.trust_level, 3)))) as trust_level,
    array_agg(distinct w.id order by w.id) as legacy_ids,
    array_remove(
      array_agg(distinct w.base_url order by w.base_url)
      || array_agg(distinct w.document_url order by w.document_url),
      null
    ) as seed_urls
  from public.web_sources w
  where nullif(btrim(w.base_url), '') is not null
  group by 1
), valid_legacy as (
  select *
  from legacy
  where domain ~ '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$'
)
insert into public.source_registry (
  source_name,
  domain,
  organization,
  access_mode,
  trust_level,
  public_only,
  robots_required,
  seed_urls,
  license_summary,
  is_active,
  legacy_web_source_ids
)
select
  source_name,
  domain,
  organization,
  'metadata_only',
  trust_level,
  true,
  true,
  seed_urls,
  'Legacy web_sources imported fail-closed; cần source owner và approval evidence trước activation.',
  false,
  legacy_ids
from valid_legacy
on conflict (domain) do update
set legacy_web_source_ids = (
      select array_agg(distinct value order by value)
      from unnest(
        source_registry.legacy_web_source_ids || excluded.legacy_web_source_ids
      ) as valueset(value)
    ),
    seed_urls = (
      select array_agg(distinct value order by value)
      from unnest(source_registry.seed_urls || excluded.seed_urls) as valueset(value)
    );

-- approved_sources có thể rỗng. Nếu có row được approve hợp lệ, chỉ row đó mới
-- có thể kích hoạt curated mode; domain vẫn được normalize và merge idempotent.
with legacy as (
  select
    a.*,
    regexp_replace(
      lower(split_part(regexp_replace(btrim(a.source_url), '^[a-z][a-z0-9+.-]*://', '', 'i'), '/', 1)),
      '^www\.',
      ''
    ) as domain
  from public.approved_sources a
  where nullif(btrim(a.source_url), '') is not null
), valid_legacy as (
  select *
  from legacy
  where domain ~ '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$'
)
insert into public.source_registry (
  source_name,
  domain,
  organization,
  access_mode,
  seed_urls,
  license_summary,
  owner_id,
  approved_by,
  approved_at,
  effective_from,
  is_active,
  legacy_approved_source_ids
)
select
  source_name,
  domain,
  source_name,
  case when approved_by is not null and approved_at is not null then 'curated' else 'metadata_only' end,
  array[source_url],
  coalesce(description, 'Legacy approved_sources import.'),
  approved_by,
  approved_by,
  approved_at,
  approved_at,
  coalesce(is_active, false) and approved_by is not null and approved_at is not null,
  array[id]
from valid_legacy
on conflict (domain) do update
set legacy_approved_source_ids = (
      select array_agg(distinct value order by value)
      from unnest(
        source_registry.legacy_approved_source_ids || excluded.legacy_approved_source_ids
      ) as valueset(value)
    ),
    seed_urls = (
      select array_agg(distinct value order by value)
      from unnest(source_registry.seed_urls || excluded.seed_urls) as valueset(value)
    ),
    access_mode = case
      when source_registry.is_active then source_registry.access_mode
      when excluded.is_active then excluded.access_mode
      else source_registry.access_mode
    end,
    owner_id = coalesce(source_registry.owner_id, excluded.owner_id),
    approved_by = coalesce(source_registry.approved_by, excluded.approved_by),
    approved_at = coalesce(source_registry.approved_at, excluded.approved_at),
    effective_from = coalesce(source_registry.effective_from, excluded.effective_from),
    is_active = source_registry.is_active or excluded.is_active;

do $legacy_reconciliation$
declare
  missing_count bigint;
begin
  select count(*)
  into missing_count
  from public.web_sources w
  where nullif(btrim(w.base_url), '') is not null
    and not exists (
      select 1
      from public.source_registry s
      where w.id = any(s.legacy_web_source_ids)
    );

  if missing_count > 0 then
    raise exception 'CRAVE-025: % web_sources legacy rows chưa được reconcile; rollback transaction.', missing_count;
  end if;
end
$legacy_reconciliation$;

alter table public.source_registry enable row level security;
alter table public.license_rules enable row level security;

do $policies$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'source_registry'
      and policyname = 'source_registry_read_effective'
  ) then
    create policy source_registry_read_effective
      on public.source_registry
      for select
      to authenticated
      using (
        (
          is_active
          and effective_from <= now()
          and (effective_until is null or effective_until > now())
        )
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'source_registry'
      and policyname = 'source_registry_insert_governance'
  ) then
    create policy source_registry_insert_governance
      on public.source_registry
      for insert
      to authenticated
      with check (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]));
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'source_registry'
      and policyname = 'source_registry_update_governance'
  ) then
    create policy source_registry_update_governance
      on public.source_registry
      for update
      to authenticated
      using (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]))
      with check (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]));
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'license_rules'
      and policyname = 'license_rules_read_effective'
  ) then
    create policy license_rules_read_effective
      on public.license_rules
      for select
      to authenticated
      using (
        (
          effective_from <= now()
          and (effective_until is null or effective_until > now())
        )
        or public.user_has_any_role(array[
          'admin'::public.user_role_name,
          'qa_manager'::public.user_role_name,
          'auditor'::public.user_role_name
        ])
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'license_rules'
      and policyname = 'license_rules_insert_governance'
  ) then
    create policy license_rules_insert_governance
      on public.license_rules
      for insert
      to authenticated
      with check (public.user_has_any_role(array[
        'admin'::public.user_role_name,
        'qa_manager'::public.user_role_name
      ]));
  end if;
end
$policies$;

do $triggers$
begin
  if not exists (
    select 1 from pg_trigger
    where tgrelid = 'public.source_registry'::regclass
      and tgname = 'source_registry_set_updated_at'
      and not tgisinternal
  ) then
    create trigger source_registry_set_updated_at
      before update on public.source_registry
      for each row execute function public.update_updated_at();
  end if;

  if not exists (
    select 1 from pg_trigger
    where tgrelid = 'public.license_rules'::regclass
      and tgname = 'license_rules_append_only_guard'
      and not tgisinternal
  ) then
    create trigger license_rules_append_only_guard
      before update or delete or truncate on public.license_rules
      for each statement execute function public.crave_block_append_only_mutation();
  end if;
end
$triggers$;

create or replace function public.resolve_source_policy_v1(
  p_url text,
  p_at timestamptz default now()
)
returns jsonb
language plpgsql
stable
security invoker
set search_path to pg_catalog, public
as $function$
declare
  v_url text := nullif(btrim(p_url), '');
  v_at timestamptz := coalesce(p_at, now());
  v_host text;
  v_source public.source_registry%rowtype;
  v_rule public.license_rules%rowtype;
  v_decision text;
begin
  if v_url is null or length(v_url) > 2048 then
    raise exception using errcode = '22023', message = 'CRAVE-025: p_url bắt buộc và tối đa 2048 ký tự.';
  end if;

  v_host := regexp_replace(
    lower(split_part(regexp_replace(v_url, '^[a-z][a-z0-9+.-]*://', '', 'i'), '/', 1)),
    '^www\.',
    ''
  );
  v_host := split_part(v_host, ':', 1);

  if v_host !~ '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$' then
    raise exception using errcode = '22023', message = 'CRAVE-025: URL/host không hợp lệ.';
  end if;

  select s.*
  into v_source
  from public.source_registry s
  where s.is_active
    and s.effective_from <= v_at
    and (s.effective_until is null or s.effective_until > v_at)
    and (v_host = s.domain or v_host like '%.' || s.domain)
  order by length(s.domain) desc
  limit 1;

  if not found then
    return jsonb_build_object(
      'matched', false,
      'domain', v_host,
      'decision', 'deny',
      'allow_fetch', false,
      'reason', 'unknown_inactive_or_expired_source'
    );
  end if;

  select r.*
  into v_rule
  from public.license_rules r
  where r.source_registry_id = v_source.id
    and r.effective_from <= v_at
    and (r.effective_until is null or r.effective_until > v_at)
    and (r.content_pattern = '*' or v_url ilike r.content_pattern escape '\')
  order by r.effective_from desc, r.created_at desc
  limit 1;

  v_decision := coalesce(v_rule.decision, v_source.access_mode);

  return jsonb_build_object(
    'matched', true,
    'source_registry_id', v_source.id,
    'source_name', v_source.source_name,
    'domain', v_source.domain,
    'decision', v_decision,
    'allow_fetch', v_decision in ('allow', 'curated'),
    'metadata_only', v_decision = 'metadata_only',
    'rule_id', v_rule.id,
    'reason', coalesce(v_rule.reason, v_source.license_summary, 'source_registry_default'),
    'public_only', v_source.public_only,
    'robots_required', v_source.robots_required,
    'crawl_delay_seconds', v_source.crawl_delay_seconds,
    'allowed_content_types', to_jsonb(v_source.allowed_content_types),
    'evaluated_at', v_at
  );
end
$function$;

comment on function public.resolve_source_policy_v1(text, timestamptz) is
  'CRAVE-025: typed source/license resolver; unknown/inactive/expired fail closed; SECURITY INVOKER.';

revoke all on public.source_registry from public, anon;
revoke all on public.license_rules from public, anon;
grant select, insert, update on public.source_registry to authenticated;
grant select, insert on public.license_rules to authenticated;

revoke all on function public.resolve_source_policy_v1(text, timestamptz) from public, anon;
grant execute on function public.resolve_source_policy_v1(text, timestamptz) to authenticated;

commit;
