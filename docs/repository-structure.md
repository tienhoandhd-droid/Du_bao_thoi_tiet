# Cấu trúc repository đích

Tài liệu này xác định vị trí nguồn chuẩn của CRAVE trong giai đoạn P0. Mục tiêu là
để mỗi loại artifact chỉ có một nguồn canon, có owner và có đường rollback rõ.

| Khu vực | Mục đích | Owner mặc định | Quy tắc |
|---|---|---|---|
| `app/` | Frontend React đang được build/deploy | Frontend | Giữ nguyên trong P0; chỉ chuyển sang `frontend/app/` bằng change package P1 riêng |
| `docs/` | Kiến trúc, governance, validation và SOP | QA/System owner | Không chứa secret hoặc report GMP thật |
| `supabase/migrations/` | Migration forward-only | Database owner | Mỗi migration có rollback cùng số tại `supabase/rollbacks/` |
| `supabase/rollbacks/` | Nguồn rollback canon | Database owner | Không sao chép rollback cạnh migration |
| `n8n/workflows/` | Export đã redaction của TKTL WF-01..WF-14 | Automation owner | Không chứa credential material; không tự import/publish |
| `n8n/release-manifest.json` | Bằng chứng capture/reconcile workflow Chat 04 | Automation owner | Không dùng thay release manifest cấp hệ thống |
| `prompts/` | Prompt có phiên bản | AI governance owner | Tệp prompt phải có tên phiên bản `vN[.N.N].md` |
| `eval/` | Dataset, fixture và báo cáo eval không nhạy cảm | Validation owner | Không commit câu hỏi, báo cáo hoặc tài liệu GMP thật |
| `scripts/` | Công cụ vận hành có thể tái lập | Platform owner | Mặc định an toàn; không ghi production nếu thiếu cờ và phê duyệt |
| `.github/` | Template và kiểm soát CI | Repository owner | Least privilege; không đưa secret vào Variables/source |

Release manifest cấp hệ thống được kiểm theo
[`docs/governance/release-manifest-contract.md`](governance/release-manifest-contract.md).
Validator không thay đổi artifact; nó chỉ đọc, kiểm tra liên kết và trả mã lỗi.

## Quy tắc chống trùng nguồn

- Mỗi migration, rollback, workflow và prompt chỉ có một đường dẫn canon.
- Nội dung dưới `eval/fixtures/` chỉ là dữ liệu giả để kiểm thử validator, không
  được import, apply hoặc publish.
- `app/` tiếp tục là frontend canon cho tới change P1 được phê duyệt; Chat 05
  không tạo bản sao tại `frontend/app/`.
- Report runtime chứa dữ liệu GMP hoặc thông tin người dùng không được commit.
