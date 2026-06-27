# Danh sách file cho Claude Code

Các file nguồn không được di chuyển hoặc nhân bản. Thư mục này là điểm vào duy
nhất để Claude Code tìm toàn bộ thay đổi và tránh review nhầm file.

| File | Loại | Mục đích |
|---|---|---|
| `supabase/migrations/015_platform_security_hardening.sql` | Nguồn thực thi | Hardening view, function ACL/search_path, audit và chat append-only |
| `supabase/migrations/015_down.sql` | Nguồn rollback | Hoàn nguyên migration 015 |
| `claude-review/platform-alignment-2026-06-27/README.md` | Gói review | Phạm vi, thứ tự và quy tắc review |
| `claude-review/platform-alignment-2026-06-27/CHECKLIST.md` | Gói review | Lỗi, hướng giải quyết, cách làm, trạng thái từng nền tảng |
| `claude-review/platform-alignment-2026-06-27/PHA-1A-SUPABASE-REVIEW.md` | Gói review | Checklist và truy vấn xác minh riêng PHA 1A |

## Hash file nguồn (sau review Claude Code 2026-06-27)

| File | SHA-256 |
|---|---|
| `supabase/migrations/015_platform_security_hardening.sql` | `f6eaaab24c15bccc3beb2cf761b27006fee5cffded043326b7db699adb4e7c41` |
| `supabase/migrations/015_down.sql` | `2433c471bee5993dbbdcd4a3894518fda4b6d6e8f77490b0f68c1b645232040d` |

Các file review (`CHECKLIST.md`, `PHA-1A-SUPABASE-REVIEW.md`, `README.md`, `FILE-MANIFEST.md`) không tính SHA vì là tài liệu, không phải SQL thực thi.

