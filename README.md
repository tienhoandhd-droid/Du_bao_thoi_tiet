# GMP Validation Dashboard — Frontend (GitHub Pages)

Repo này **chỉ chứa frontend**. Backend (workflow n8n, SQL Supabase) KHÔNG nằm ở đây.

## Cách hoạt động
`index.html` chứa 3 placeholder → GitHub Actions thay bằng Secrets lúc deploy → publish lên Pages.
Source code KHÔNG chứa key nào.

## Cài đặt (giao diện web, không dòng lệnh)

### 1. Tạo repo
github.com → New repository → tên `gmp-validation-dashboard` → **Private** → Create.

### 2. Upload file
- **Add file ▸ Upload files** → kéo-thả `index.html` → Commit.
- **Add file ▸ Create new file** → gõ đúng đường dẫn `.github/workflows/deploy.yml` → dán nội dung file deploy.yml → Commit.
  *(Cách tạo-file này chắc ăn hơn kéo-thả thư mục `.github` vì hệ điều hành hay ẩn thư mục bắt đầu bằng dấu chấm.)*

### 3. Thêm 3 Secrets
Settings ▸ Secrets and variables ▸ Actions ▸ New repository secret:

| Secret | Giá trị | Lấy ở |
|--------|---------|-------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Supabase ▸ Settings ▸ API ▸ Project URL |
| `SUPABASE_ANON_KEY` | `eyJ...` (chuỗi dài) | Supabase ▸ Settings ▸ API ▸ **anon public** key |
| `WEBHOOK_BASE` | `https://<n8n-host>/webhook` | URL gốc webhook n8n (KHÔNG đuôi `/health`) |

> Dùng **anon public** key (an toàn cho frontend nhờ RLS), KHÔNG dùng service_role.

### 4. Bật Pages
Settings ▸ Pages ▸ Source = **GitHub Actions** ▸ Save.

### 5. Deploy
Actions ▸ "Deploy to GitHub Pages" ▸ Run workflow. Đợi ✅ → URL ở Settings ▸ Pages:
`https://<username>.github.io/gmp-validation-dashboard/`

### 6. Supabase redirect
Authentication ▸ URL Configuration ▸ Redirect URLs ▸ Add:
`https://<username>.github.io/gmp-validation-dashboard/**`

## Điều kiện để dashboard chạy
- Workflow n8n bản **Cách B + CORS** đã Active (CORS đã nhúng sẵn — frontend gọi được).
- Đã nạp dữ liệu RAG (theo RUNBOOK-CHAT05) để rag-query có trích dẫn.

## Xử lý lỗi nhanh
| Lỗi | Sửa |
|-----|-----|
| Actions ❌ đỏ | Kiểm 3 Secrets đúng tên |
| 404 khi mở trang | Settings ▸ Pages ▸ Source = GitHub Actions |
| Console báo CORS | Workflow chưa Active, hoặc import nhầm bản chưa-CORS |
| Đăng nhập lỗi | Sai `SUPABASE_URL`/`SUPABASE_ANON_KEY` |
| "Không kết nối được" | Sai `WEBHOOK_BASE` |
