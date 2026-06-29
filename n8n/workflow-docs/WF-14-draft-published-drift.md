# WF-14 — Tavily credential và draft/published drift

## Trạng thái sau remediation

- Workflow ID: `6USn5CYpK9VlyExu`.
- Draft version: `4f2f07d4-da78-4196-a70a-80510ac6fbd2`.
- Active version: `4f2f07d4-da78-4196-a70a-80510ac6fbd2`.
- Draft/active drift: **không còn**.
- Graph: 15 node, 14 connection; node/connection topology không đổi.
- `CONFIG` chỉ còn `max_results`, `snippet_max`, `max_query_length`; không còn `tavily_api_key`.
- `Parse + Validate` và `Prepare Tavily Body` không phát sinh hoặc gửi `api_key`/`tavily_api_key`.
- Node `🌐 Tavily Search` dùng Header Auth credential `CRAVE-Tavily`, giới hạn domain `api.tavily.com`.
- Node `🔐 Verify JWT` dùng GET `/auth/v1/user`, có Authorization + apikey và `onError=continueErrorOutput`.

## Evidence thực thi

- Negative JWT test trên test webhook, không có token: HTTP **401**, không đi vào Tavily.
- Positive test `1451221`: PASS; dùng JWT pin + audit pin, Tavily chạy thật qua credential mới, không ghi Supabase.
- Sau khi bỏ field `tavily_api_key` rỗng khỏi `Parse + Validate`, positive regression test `1451310`: PASS.
- Tavily Dashboard ghi nhận key mới tiêu tốn 4 credits cho hai lượt advanced search test.
- Key cũ tên `default` đã bị revoke; Dashboard chỉ còn key `crave-wf14-2026-06-29`.

## Secret handling

- API key mới không xuất hiện trong source, Git, Issue, PR, tool output hoặc tài liệu.
- MCP sanitize credential material; source chỉ lưu credential reference ID/name.
- Supabase anon key tiếp tục được redaction bằng `__REDACTED_SUPABASE_ANON_KEY__`.

## Quyết định source

`n8n/workflows/TKTL-WF-14-web-document-search.json` đại diện activeVersion `4f2f07d4-da78-4196-a70a-80510ac6fbd2`, đặt `active=false` làm guard import. Credential material không nằm trong JSON canonical.

## Rollback

- Version trước remediation: `70afe9fe-2325-4413-a1b1-860f0c05cb2f` chỉ dùng làm evidence lịch sử, không nên publish lại vì chứa literal key đã revoke và thiếu JWT error branch.
- Nếu credential mới lỗi, dừng publish/execute và sửa binding `CRAVE-Tavily`; không phục hồi key cũ.
- Mọi rollback/publish live tiếp theo vẫn cần change-control và xác nhận riêng.
