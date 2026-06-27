# WF-10 Google Drive — Quyết định hoãn

## Trạng thái quyết định

WF-10 Google Drive **không được triển khai trong Chat 15**. Hạng mục này không tạo
`n8n/WF-10.json`, không import workflow và không kích hoạt endpoint mới trên n8n.

## Lý do hoãn

CRAVE chỉ cho phép hai credential n8n:

1. `GMP-check` — Postgres, ID `0WcJFXEhwLXQhJmn`.
2. `OpenAl` — OpenAI, ID `r5CCCyYKeJDjnJ0A`.

Tích hợp Google Drive theo cách chuẩn cần thêm Google OAuth2 hoặc Google Service
Account credential trong n8n. Đây sẽ là credential thứ ba và vi phạm ràng buộc
cứng của hệ thống. Community node cũng không được phép sử dụng.

Môi trường n8n hiện tại đồng thời chặn `require('crypto')` và
`globalThis.crypto.subtle`, nên không thể dùng cách ký JWT thông thường trong Code
node để thay thế credential Google.

Vì vậy, triển khai WF-10 ở thời điểm này tạo ra một trong hai vi phạm: thêm
credential thứ ba hoặc đưa cơ chế ký/secret chưa được kiểm chứng vào workflow.
Quyết định an toàn là hoãn WF-10.

## Lối vòng đề xuất cho hạng mục sau

Phương án cần làm POC là dùng service account Google và tự tạo, ký JWT assertion
inline trong biểu thức của HTTP Request node để:

1. Gửi JWT assertion đến Google OAuth 2.0 token endpoint để lấy access token ngắn
   hạn.
2. Gọi Google Drive REST API bằng access token vừa nhận.
3. Không tạo Google credential thứ ba và không dùng community node.

Về kỹ thuật, có thể hiện thực phần ký JWT bằng biểu thức JavaScript thuần ngay trong
HTTP Request node và tương thích sandbox. Tuy nhiên, phương án này cần thêm thời
gian để thiết kế và kiểm chứng các điểm sau:

- Cách cấp private key an toàn mà không hard-code secret vào workflow, frontend
  hoặc source code, đồng thời vẫn tuân thủ giới hạn hai credential và không dùng
  n8n Variables.
- Tính đúng đắn của RS256/JWT trong sandbox không có module `crypto`.
- Cơ chế xoay vòng/revoke khóa, giới hạn scope và quyền thư mục Drive theo nguyên
  tắc tối thiểu.
- Xử lý thời gian sống token, retry, rate limit, lỗi một phần và idempotency khi
  đồng bộ tệp.
- Audit trail append-only, truy nguyên người khởi tạo và bằng chứng đồng bộ theo
  yêu cầu ALCOA+.
- Threat model và review bảo mật trước khi cho phép chạy trên môi trường thật.

Private key service account không được đưa trực tiếp vào JSON workflow hoặc commit
vào repository trong bất kỳ trường hợp nào.

## Phạm vi dự kiến của hạng mục tiếp theo

Hạng mục kế tiếp dành riêng cho WF-10 cần bao gồm:

1. POC ký JWT và đổi access token trong đúng sandbox n8n hiện hành.
2. Thiết kế kênh cấp secret đáp ứng ràng buộc bảo mật và hai credential.
3. Xác định scope Google Drive tối thiểu và thư mục được phép truy cập.
4. Thiết kế workflow prefix `TKTL`, Cách B byte-identical cho xác thực người dùng
   nếu workflow có webhook, và chỉ dùng node native.
5. Test lỗi, retry, idempotency, audit log append-only và kiểm tra không rò rỉ
   private key trong execution log.
6. Cho người dùng xem workflow và kết quả POC trước khi import, execute hoặc
   publish trên `n8n.cpc1hn.com`.

Cho đến khi các điều kiện trên được hoàn tất và phê duyệt, WF-10 tiếp tục ở trạng
thái **POSTPONED**.
