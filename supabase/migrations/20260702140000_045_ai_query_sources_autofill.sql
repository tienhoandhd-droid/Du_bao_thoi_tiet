-- CRAVE deploy migration: 20260702140000_045_ai_query_sources_autofill
-- Semantic source ID: CRAVE-045 / autofill lineage + hạ grounded khi thiếu bằng chứng
-- Project: bdttccztjtrcaztjgkot
--
-- Khi retrieval lần đầu trả kết quả thật (LAMSAFE), WF-02 lưu citation vào
-- ai_query_sources nhưng: (a) KHÔNG set document_version_id → validator CRAVE-030B
-- báo "citation không khớp lineage"; (b) grounded=true nhưng chưa có
-- retrieval_candidate_id/citation_verified_at → vi phạm grounded_verification_check.
--
-- Fix (BEFORE INSERT, chạy TRƯỚC validator nhờ tên 'aa_'):
--   - tự điền document_version_id ĐÚNG từ chunk (không bịa — lấy lineage thật).
--   - hạ grounded=false khi CHƯA đủ chuỗi bằng chứng (trung thực; không bypass
--     validator lineage — chỉ phản ánh đúng mức độ verified hiện có).

begin;

do $guard$
begin
  if to_regclass('public.ai_query_sources') is null then
    raise exception 'CRAVE-045: thiếu ai_query_sources.';
  end if;
end
$guard$;

create or replace function public.crave_autofill_ai_query_source()
returns trigger
language plpgsql
security invoker
set search_path = public, extensions
as $$
begin
  -- điền document_version_id đúng theo chunk (lineage thật)
  if new.chunk_id is not null and new.document_version_id is null then
    select dc.document_version_id into new.document_version_id
    from public.document_chunks dc where dc.id = new.chunk_id;
  end if;

  -- grounded=true chỉ hợp lệ khi đủ chuỗi bằng chứng; nếu chưa → hạ false (trung thực)
  if new.grounded is true
     and (new.retrieval_candidate_id is null or new.citation_verified_at is null) then
    new.grounded := false;
  end if;

  return new;
end
$$;

comment on function public.crave_autofill_ai_query_source() is
  'CRAVE-045: BEFORE INSERT ai_query_sources — tự điền document_version_id từ chunk (lineage thật) + hạ grounded=false khi chưa đủ bằng chứng. Chạy trước validator lineage.';

drop trigger if exists ai_query_sources_aa_autofill on public.ai_query_sources;
create trigger ai_query_sources_aa_autofill
  before insert on public.ai_query_sources
  for each row execute function public.crave_autofill_ai_query_source();

commit;
