# Đề xuất: Branch Protection Policy cho nhánh main

**Tài liệu:** GOVERNANCE-GITHUB-001
**Phiên bản:** 1.0 — 2026-06-28
**Owner:** Claude Code — Chat 02
**Trạng thái:** ĐỀ XUẤT — chờ người dùng duyệt và thao tác thủ công trên GitHub Settings

---

## Lý do

Hiện tại nhánh `main` chưa có bảo vệ:
- Bất kỳ thành viên nào cũng có thể push thẳng vào `main`
- Không có required review trước khi merge
- Force push không bị chặn → có thể ghi đè lịch sử commit
- CI không phải điều kiện bắt buộc để merge

---

## Cấu hình đề xuất

Vào **Settings → Branches → Add branch protection rule** → Branch name pattern: `main`

| Tùy chọn | Giá trị đề xuất | Lý do |
|----------|----------------|-------|
| Require a pull request before merging | ✅ Bật | Mọi thay đổi phải qua PR |
| Required approvals | 1 | Nhóm <10 người — 1 review đủ |
| Dismiss stale pull request approvals | ✅ Bật | Tránh approve rồi push thêm code |
| Require status checks to pass | ✅ Bật | CI phải PASS trước khi merge |
| Required status checks | `CI — TypeScript Build & Lint` (từ `ci.yml`) | Đảm bảo build không vỡ |
| Require branches to be up to date | ✅ Bật | Tránh merge code cũ |
| Do not allow bypassing the above settings | ✅ Bật | Kể cả admin |
| Allow force pushes | ❌ Tắt | Bảo vệ lịch sử commit |
| Allow deletions | ❌ Tắt | Không xóa nhánh main |

---

## Thứ tự thực hiện

1. **Trước tiên:** Đảm bảo `ci.yml` đã có trong nhánh `main` (merge PR từ Chat 02)
2. **Sau đó:** Vào GitHub Settings → Branches → Thêm rule theo bảng trên
3. **Verify:** Thử tạo PR thử nghiệm → xác nhận CI chạy và require review

> Không thêm branch protection trước khi `ci.yml` đã merge — nếu không, mọi PR sau đều bị HOLD vì required check `CI — TypeScript Build & Lint` chưa tồn tại.

---

## Tình huống đặc biệt

**Khi cần hotfix khẩn cấp:**
- Tạo branch `hotfix/<issue>-<ten-ngan>` → PR → yêu cầu review nhanh → merge
- Không dùng "bypass" để push thẳng trừ khi hệ thống production đang sập và không có cách khác
- Sau hotfix: tạo retrospective issue ghi lý do bypass (nếu có)

**Khi chỉ có 1 người trong nhóm:**
- Self-review: tạo PR → tự review kỹ → merge sau ít nhất 10 phút (tránh merge vội)
- Ghi checklist DoD vào PR description trước khi merge

---

## Liên quan

- `docs/sop/github-secret-rotation.md` — quản lý secrets
- `kehoach.md §2 Nguyên tắc 1` — GitHub-first flow bắt buộc
- `nangcap.md §5.1 P0-B` — branch protection là blocker P0
