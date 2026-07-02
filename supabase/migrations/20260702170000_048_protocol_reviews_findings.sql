-- CRAVE-048: lưu findings chi tiết cho protocol_reviews (WF-04) — trước đây tính rồi mất.
begin;
alter table public.protocol_reviews add column if not exists findings jsonb;
comment on column public.protocol_reviews.findings is 'CRAVE-048: chi tiết findings (rule/template/semantic) từ WF-04 Check Protocol — truy vết.';
commit;
