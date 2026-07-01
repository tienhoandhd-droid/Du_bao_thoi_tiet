# GMP Validation Intelligence Dashboard

Hệ thống quản lý tài liệu và tra cứu thông tin GMP (Good Manufacturing Practice) có tích hợp AI, được xây dựng cho ngành dược phẩm / sản xuất.

## Điều hướng dự án

- System master plan: [`docs/architecture/crave-system-master-plan.md`](docs/architecture/crave-system-master-plan.md)
- Kế hoạch nâng cấp tìm kiếm: [`docs/architecture/search-upgrade-master-plan.md`](docs/architecture/search-upgrade-master-plan.md)
- Đề xuất tìm kiếm đa phương thức (tài liệu/hình/sơ đồ/bảng): [`docs/upgrade/PROPOSAL-document-search-multimodal.md`](docs/upgrade/PROPOSAL-document-search-multimodal.md)
- Supabase schema plan: [`docs/database/supabase-master-schema-plan.md`](docs/database/supabase-master-schema-plan.md)
- Data contracts: [`docs/database/data-contract-matrix.md`](docs/database/data-contract-matrix.md)

> Trạng thái production/search readiness còn **HOLD**; danh sách tính năng dưới
> đây không tự chứng minh rằng mọi capability đã qua validation.

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

## Cấu trúc thư mục chính

```
├── index.html          # Trang chính (vanilla)
├── styles.css
├── js/
│   ├── app.js          # Logic ứng dụng
│   └── config.js       # Biến môi trường (inject lúc build)
├── app/                # Frontend React/TypeScript
├── supabase/           # Migrations, rollbacks, tests, schema contracts
├── n8n/                # Redacted TKTL workflows, contracts, payloads, manifest
├── prompts/            # Versioned prompt families
├── eval/               # Golden datasets, fixtures and reports
├── scripts/            # Backup/ingest/health/audit/schema validation
└── docs/               # Architecture, database, governance, progress, checkpoints
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

## Ràng buộc an toàn GMP (bất biến)

Các quy tắc kỹ thuật không được vi phạm khi phát triển/vận hành hệ thống:

1. **Không hard-code hoặc in secret/token/key** trong source, log hay frontend; anon key được phép.
2. **Chỉ workflow `TKTL`** tại n8n (`n8n.cpc1hn.com`); không đụng các nhóm workflow khác.
3. **JWT n8n dùng Cách B:** `GET /auth/v1/user` + `apikey` + `onError=continueErrorOutput`; verify token thật (ES256).
4. **AI retrieval chỉ qua controlled retrieval path** (`hybrid_search_v3`/v4); không raw-select nội dung controlled để đưa thẳng vào LLM.
5. **AI output GMP luôn là DRAFT** — AI không có quyền approve; human sign-off bắt buộc.
6. **Audit/retrieval/tool/review evidence là append-only** (chỉ INSERT).
7. **Migration phải có rollback + verify + test** tương ứng; không hạ test/bỏ control để "làm xanh giả".
8. **Xử lý tài liệu GMP local/private** — không upload tài liệu lên dịch vụ cloud/demo.

> **Thao tác live cần xác nhận trước:** apply migration Supabase, n8n update/execute/
> publish/archive, Git push/PR — trình exact change set và chờ đồng ý.
