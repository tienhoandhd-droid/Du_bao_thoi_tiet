-- CRAVE-027 negative runtime test. Mọi mutation đều được bắt lỗi và ROLLBACK.
begin;

do $negative$
declare
  version_a public.document_versions%rowtype;
  document_b_id uuid;
  version_b_id uuid;
  blocked boolean;
begin
  select * into strict version_a
  from public.document_versions
  where record_origin='legacy_backfill_027'
  order by id
  limit 1;

  select d.id, d.current_version_id
  into strict document_b_id, version_b_id
  from public.documents d
  where d.id <> version_a.document_id
  order by d.id
  limit 1;

  blocked := false;
  begin
    delete from public.document_versions where id=version_a.id;
  exception when others then
    blocked := sqlerrm like 'CRAVE-027:%DELETE%';
  end;
  if not blocked then
    raise exception 'CRAVE-027 negative: DELETE không bị immutability trigger chặn.';
  end if;

  blocked := false;
  begin
    update public.document_versions
    set version_label=version_label || '-forbidden'
    where id=version_a.id;
  exception when others then
    blocked := sqlerrm like 'CRAVE-027:%không được sửa%';
  end;
  if not blocked then
    raise exception 'CRAVE-027 negative: identity update không bị chặn.';
  end if;

  blocked := false;
  begin
    update public.document_versions
    set approved_for_ai_use=true
    where id=version_a.id;
  exception when check_violation then
    blocked := true;
  end;
  if not blocked then
    raise exception 'CRAVE-027 negative: false approval không bị constraint chặn.';
  end if;

  blocked := false;
  begin
    update public.documents
    set current_version_id=version_a.id
    where id=document_b_id;
  exception when others then
    blocked := sqlerrm like 'CRAVE-027:%cùng logical document%';
  end;
  if not blocked then
    raise exception 'CRAVE-027 negative: cross-document current pointer không bị chặn.';
  end if;

  if not exists (
    select 1 from public.documents
    where id=document_b_id and current_version_id=version_b_id
  ) then
    raise exception 'CRAVE-027 negative: current pointer thay đổi ngoài ý muốn.';
  end if;
end
$negative$;

rollback;
