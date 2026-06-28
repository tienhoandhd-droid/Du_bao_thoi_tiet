# WF-14 — Tavily và draft/published drift

## Bằng chứng live read-only

- Workflow ID: `6USn5CYpK9VlyExu`.
- Draft version: `f432217d-c329-45cd-90a7-2a0055719549`.
- Active version: `70afe9fe-2325-4413-a1b1-860f0c05cb2f`.
- Cả draft và active có 15 node; active có 14 connection.
- Node `CONFIG` chứa literal Tavily secret trên live. Giá trị không được ghi vào repo hoặc tài liệu; export thay bằng `__REDACTED_TAVILY_API_KEY__`.
- Node `🔐 Verify JWT` gọi đúng GET `/auth/v1/user`, có Authorization và apikey, nhưng **thiếu** `onError=continueErrorOutput` ở cả graph đã quan sát.

## Bản chất drift

Node names/types và connection topology giữa draft và active trùng nhau. Khác biệt nằm ở serialization/default parameter tại 11 đường dẫn (ví dụ method GET được khai báo tường minh ở active, mode của Set/Code, contentType JSON và các object options rỗng). Dù nhiều khác biệt có thể tương đương về runtime, version ID vẫn khác nên phải coi là drift cho tới khi có change-control/publish có chủ đích.

## Quyết định source

`n8n/workflows/TKTL-WF-14-web-document-search.json` đại diện activeVersion đang chạy, đã redaction. Không tự “nâng” draft lên active, không sửa live và không giả định draft là bản canonical.

## Hành động live cần phê duyệt riêng (chưa thực hiện)

1. Rotate/revoke Tavily key đã từng tồn tại dạng literal.
2. Quyết định credential governance cho `CRAVE-Tavily`; không lách qua CONFIG.
3. Sửa JWT error branch thành `onError=continueErrorOutput`, test âm 401/invalid token.
4. Review diff draft/active, sau đó publish đúng version theo change-control nếu được duyệt.
