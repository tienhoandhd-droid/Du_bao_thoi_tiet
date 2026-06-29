# WF-06 Document Search — security review

**Ngày review:** 2026-06-29
**Workflow:** `TKTL WF-06 Document Search`
**Workflow ID:** `o4fuUanxRrD7qQoG`
**Live version:** `f7b7ee5a-870b-446d-9a1e-e06ff1f4fe22`
**Source:** `n8n/workflows/TKTL-WF-06-document-search.json`
**Trạng thái:** **HOLD — cần remediation hoặc test âm trước GO CYCLE 2**

## 1. Bằng chứng đã kiểm

- n8n MCP read-only trả workflow active, không archived.
- `versionId` và `activeVersionId` cùng bằng `f7b7ee5a-870b-446d-9a1e-e06ff1f4fe22`.
- Graph live khớp source theo đường chính:
  `Webhook Search` → `🔐 Verify JWT` → `Parse + Build SQL` → `OK?` →
  `PG: Search Documents` → `Format Results` → `Search Response`.
- Node `🔐 Verify JWT` gọi Supabase `/auth/v1/user` và có
  `onError=continueErrorOutput`.
- Không update, execute hoặc publish workflow trong review này.

## 2. Finding

### F-06-01 — Dynamic SQL từ request body

Node `Parse + Build SQL` tự nối chuỗi SQL cho nhiều filter:

- enum cast: `document_type`, `source_type`, `language_code`, `status`,
  `translation_status`;
- text filter: `equipment_type`, `equipment_code`, `owner_department`;
- keyword ILIKE;
- pagination `limit`/`offset`.

Một số text field có escape dấu `'`, nhưng enum field không được allowlist trước
khi đưa vào SQL. Vì query được đưa vào Postgres node dạng executeQuery, đây vẫn là
rủi ro injection/SQL error surface nếu input độc hại hoặc enum cast bị lạm dụng.

**Mức độ:** P1/P0 tùy credential boundary. Nếu Postgres credential có quyền rộng
hoặc bypass RLS, finding này là P0.

### F-06-02 — Code node tự decode JWT không verify chữ ký

Workflow đã có node `🔐 Verify JWT` trước `Parse + Build SQL`, đây là điểm tốt.
Tuy nhiên `Parse + Build SQL` vẫn tự decode JWT payload bằng base64 để lấy `sub`.
Trong source hiện tại `userId` không được dùng tiếp để filter dữ liệu, nên decode
này không tạo authorization control thật. Nó có thể gây hiểu nhầm rằng workflow đã
verify token trong Code node.

**Mức độ:** P2 nếu verify node luôn đứng trước query và onError đúng; tăng lên P1
nếu sau này logic dùng `userId` decoded này cho authorization.

### F-06-03 — Authorization boundary chưa chứng minh bằng DB/RLS evidence

WF-06 dùng Postgres credential `GMP-check` để SELECT trực tiếp bảng `documents`.
Review source không chứng minh được:

- credential có bị RLS bypass không;
- policy `documents` có ràng buộc user/document access không;
- `include_superseded=true` có phù hợp vai trò người gọi không;
- response có trả metadata không được phép cho user thường không.

**Mức độ:** P1/P0 tùy kết quả Supabase read-only verification.

### F-06-04 — Webhook CORS đang `allowedOrigins: "*"`

Webhook cho phép mọi origin. JWT vẫn là control chính, nhưng với endpoint tài liệu
GMP, cần quyết định rõ đây là intended public API hay chỉ frontend CRAVE được gọi.

**Mức độ:** P2/P1 tùy threat model.

## 3. Test âm cần có trước PASS

Không execute workflow trong review này. Trước khi đóng finding cần có evidence:

1. Request thiếu token → 401.
2. Request token invalid/expired → 401 và không chạy Postgres node.
3. Enum injection payload, ví dụ `document_type` chứa ký tự phá cast → không thực
   thi SQL ngoài ý định; response không lộ SQL/internal error.
4. Keyword injection payload → không làm thay đổi WHERE ngoài ILIKE mong muốn.
5. User thường không đọc được document ngoài quyền, nếu hệ thống có
   `document_access`.
6. `include_superseded=true` chỉ được phép cho role phù hợp hoặc bị bỏ qua cho
   user thường.
7. Response không trả field nhạy cảm ngoài contract đã duyệt.

## 4. Remediation đề xuất

Ưu tiên an toàn:

1. Chuyển search documents sang RPC Supabase/Postgres server-side, ví dụ
   `search_documents_v1`, nhận tham số typed và dùng SQL parameterization.
2. Trong RPC, validate enum bằng type cast an toàn hoặc allowlist trước khi query.
3. Áp dụng authorization ở DB layer: `auth.uid()`/role/document access, không dựa
   vào JWT decoded trong n8n Code node.
4. n8n chỉ gọi RPC với tham số JSON sạch; không tự build SQL string.
5. Ghi audit append-only cho search nếu query tài liệu regulated cần traceability.
6. Nếu vẫn giữ direct SQL tạm thời, phải allowlist enum trong Code node và không
   đưa raw request vào SQL.

## 5. Kết luận

WF-06 không còn là “unknown”: live/source đã được xác nhận read-only, auth node
đứng trước query và có error branch đúng. Nhưng do dynamic SQL + DB authorization
boundary chưa được chứng minh, review kết luận:

**HOLD — cần remediation hoặc negative test evidence trước GO CYCLE 2.**
