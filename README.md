# GMP Validation Intelligence Dashboard

Hệ thống quản lý tài liệu và tra cứu thông tin GMP (Good Manufacturing Practice) có tích hợp AI, được xây dựng cho ngành dược phẩm / sản xuất.

## Tính năng chính

- **AI Search / Q&A** — Tra cứu tài liệu GMP bằng ngôn ngữ tự nhiên (RAG qua n8n webhook + OpenAI)
- **Thư viện tài liệu** — Quản lý SOP, Guideline, Form/Template theo trạng thái duyệt
- **Audit Trail** — Nhật ký toàn bộ hành động người dùng, append-only
- **Dashboard tổng quan** — Thống kê tài liệu, AI queries, cảnh báo hệ thống
- **Kiểm tra bảo mật** — Xác minh RLS, JWT, HTTPS, service_role key exposure
- **Phân quyền theo vai trò** — admin, qa_manager, validation, engineering, viewer, auditor

## Công nghệ

| Layer | Stack |
|---|---|
| Frontend (main) | Vanilla JS + HTML/CSS |
| Frontend (v2) | Vite + React + TypeScript + Tailwind CSS + shadcn/ui |
| Auth & Database | Supabase (PostgreSQL + RLS) |
| AI / Automation | n8n webhooks |
| CI/CD | GitHub Actions + GitHub Secrets |

## Cấu trúc thư mục

```
├── index.html          # Trang chính (vanilla)
├── styles.css
├── js/
│   ├── app.js          # Logic ứng dụng
│   └── config.js       # Biến môi trường (inject lúc build)
└── app/                # Phiên bản React/TypeScript (đang phát triển)
    └── src/App.tsx
```

## Cài đặt & Triển khai

### Biến môi trường

Tạo các GitHub Secrets / Repository Variables:

| Tên | Mô tả |
|---|---|
| `SUPABASE_URL` | URL của Supabase project |
| `SUPABASE_ANON_KEY` | Anon key (public-safe) |
| `WEBHOOK_BASE` | Base URL của n8n webhook |

GitHub Actions sẽ tự động inject các giá trị này vào `js/config.js` lúc build.

### Chạy local (app React/TypeScript)

```bash
cd app
npm install
cp .env.example .env.local   # điền VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_WEBHOOK_BASE
npm run dev
```

## Bảo mật

- Frontend chỉ dùng **anon key** (không bao giờ expose service_role key)
- Mọi truy vấn dữ liệu đi qua **Row Level Security (RLS)** của Supabase
- API calls tới n8n đều kèm **JWT Bearer token**
- Phiên đăng nhập tự động hết hạn sau **8 giờ**
