# CRAVE — File ownership và lease Chat 01–05

**Hiệu lực:** từ 2026-06-29 đến System Check S1 hoặc khi có quyết định điều phối mới được ghi trong change register<br>
**Nguồn:** yêu cầu Chat 01 ngày 2026-06-29 và [`kehoach.md §5–6`](../../kehoach.md)<br>
**Mục tiêu:** bảo đảm mỗi file/path có một owner duy nhất trong chu kỳ 1

## 1. Quy tắc lease

- Chỉ owner của Chat được tạo/sửa các path thuộc lease của Chat đó. Agent khác chỉ đọc.
- Không mở rộng glob hoặc “tiện tay” sửa file ngoài lease. Nếu cần giao nhau, dừng và ghi `[!] Chưa giải quyết` trong [`change-register.md`](change-register.md).
- Lease mô tả quyền sửa source, không tự cấp quyền push, merge, apply migration, update/publish n8n hoặc đổi GitHub settings.
- File có sẵn vẫn thuộc owner được ghi trong bảng trong thời gian lease; trạng thái “đã hoàn thành” không cho Chat khác sửa lại trước S1.
- Với thư mục scaffold, owner chỉ tạo khung theo Chat card; nội dung thuộc Chat sau vẫn do owner Chat sau quản lý.

## 2. Bảng lease

| Chat | Owner | File/path lease độc quyền | Trạng thái tại 2026-06-29 | Ghi chú ranh giới |
|---:|---|---|---|---|
| 01 | **Codex GPT** | `docs/governance/change-register.md`<br>`docs/governance/file-ownership.md`<br>`docs/architecture/current-state-snapshot.md` | **Đang hoàn tất local** | Chỉ tài liệu baseline/governance; không thay đổi production hoặc remote |
| 02 | **Claude Code** | `.github/workflows/eval.yml`<br>`.github/workflows/ci.yml`<br>`docs/sop/github-secret-rotation.md`<br>`docs/governance/github-branch-policy.md` | **ĐÃ HOÀN THÀNH** | Hoàn thành trước Chat 01 vì P0-A; live state được ghi hồi tố trong change register |
| 03 | **Codex GPT** | `supabase/baseline/`<br>`supabase/migrations/022_*.sql`<br>`supabase/rollbacks/022_*_down.sql`<br>`docs/architecture/supabase-source-map.md` | **Kế hoạch** | Chỉ source/reconciliation; không apply migration nếu chưa trình bày kế hoạch và được xác nhận |
| 04 | **Claude Code** | `n8n/workflows/`<br>`n8n/workflow-docs/`<br>`n8n/release-manifest.json` | **Kế hoạch** | Chỉ workflow prefix TKTL; không update/execute/publish/unpublish/archive khi chưa được xác nhận |
| 05 | **Codex GPT** | `docs/` *(scaffold, trừ các file/path đã lease ở Chat 01–04)*<br>`prompts/` *(scaffold)*<br>`eval/` *(scaffold)*<br>`scripts/` *(scaffold)*<br>`.github/ISSUE_TEMPLATE/`<br>`.github/pull_request_template.md` | **Kế hoạch** | Không ghi đè tài liệu Chat 01/02/03/04; chỉ scaffold theo Chat 05 card |

## 3. Xử lý chồng lấn

Thứ tự ưu tiên khi một glob rộng chồng lên file/path cụ thể:

1. Lease file cụ thể thắng lease thư mục/glob.
2. Lease Chat đang thực hiện và được ghi trong change register thắng scaffold của Chat 05.
3. Nếu vẫn mơ hồ, không sửa; owner ghi blocker và yêu cầu điều phối trước khi tiếp tục.

Ví dụ: `docs/` của Chat 05 không bao gồm ba file Chat 01, hai runbook Chat 02 hoặc `docs/architecture/supabase-source-map.md` của Chat 03.

## 4. Ma trận bàn giao

| Từ | Sang | Điều kiện bàn giao |
|---|---|---|
| Chat 01 | Chat 03 | Snapshot + register + lease tồn tại; diff chỉ ba file Chat 01; không có secret value |
| Chat 02 | Chat 03/04/05 | Evidence P0-A được ghi hồi tố; các file Chat 02 chỉ đọc, không sửa |
| Chat 03 | Chat 04 | Source map/baseline/022 source và rollback có evidence; không ngụ ý đã apply live |
| Chat 04 | Chat 05 | Workflow export đã redaction; manifest có version/source; không ngụ ý đã publish |
| Chat 05 | System Check S1 | Scaffold không ghi đè lease cũ; S1 kiểm tra tích hợp read-only toàn bộ Chat 01–05 |

## 5. Trạng thái lease cuối Chat 01

- [x] **Đã hoàn thành:** lease Chat 01–05 đã được ghi với owner và ranh giới cụ thể.
- [ ] **Kế hoạch:** giải phóng hoặc gia hạn lease tại System Check S1 dựa trên evidence thực tế.
- [!] **Chưa giải quyết:** Issue/branch/PR provenance của Chat 02 chưa được cung cấp; điều này không đổi quyền sở hữu file nhưng phải bổ sung vào change register khi có bằng chứng.
