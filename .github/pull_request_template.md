## Mục tiêu

<!-- Mô tả change package, intended use và giá trị. Không dán secret/dữ liệu GMP thật. -->

## Phạm vi

- Chat / System Check:
- Issue liên quan:
- File/hệ thống thuộc phạm vi:
- File/hệ thống chủ ý không thay đổi:

## Bằng chứng kiểm thử

- [ ] Syntax/lint/build phù hợp đã PASS.
- [ ] Positive test đã PASS.
- [ ] Negative test đã PASS.
- [ ] Secret scan toàn diff đã PASS và không in matched value.
- [ ] Release manifest/hash đã kiểm nếu change ảnh hưởng migration, workflow, prompt, model hoặc dataset.
- [ ] Eval gate đã chạy nếu change ảnh hưởng retrieval/prompt/workflow/model.

## GMP, bảo mật và traceability

- [ ] AI output vẫn là DRAFT; AI không approve.
- [ ] Audit append-only, RLS/grants và JWT Cách B không bị suy giảm hoặc N/A.
- [ ] Không có credential material trong source; chỉ dùng credential whitelist.
- [ ] Không có source-runtime drift mới chưa được ghi nhận.
- [ ] Không chứa báo cáo/câu hỏi/tài liệu GMP thật trong repo public.

## Thao tác live

<!-- Đánh dấu đúng trạng thái. Một PR được merge không mặc nhiên phê duyệt thao tác live. -->

- [ ] Không có thao tác Supabase/n8n/GitHub settings live.
- [ ] Có thao tác live và đã ghi phê duyệt riêng + evidence đã redaction bên dưới.

Phê duyệt/evidence live:

## Rollback

<!-- Nêu Git revert, migration rollback, workflow version rollback và dữ liệu cần giữ. -->

## Reviewer gate

- [ ] Owner phạm vi đã review.
- [ ] Claude Code/Codex self-check 8 mục đã PASS.
- [ ] System Check tương ứng đã GO hoặc chưa đến checkpoint.
