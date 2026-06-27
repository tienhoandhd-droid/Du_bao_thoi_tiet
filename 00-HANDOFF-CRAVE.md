# ❄ HANDOFF — GMP VALIDATION INTELLIGENCE DASHBOARD (Mô hình CRAVE)
## Tài liệu mốc nối giữa các đoạn chat (master handoff)

**Chủ trì:** DS. Tào Tiến Hoàn — V/Q Team, QLCL, CPC1 Hà Nội
**Stack hiện tại:** Supabase PostgreSQL 16 + pgvector · n8n self-hosted (sandbox khoá crypto) · OpenAI gpt-4o-mini · GitHub Pages
**Stack hệ mới (đang chuyển sang):** + Frontend **TypeScript** (Vite + React + Tailwind + shadcn/ui, build trong GitHub Actions) · Backend **agentic** (node AI Agent native + memory Postgres)
**Cập nhật gần nhất:** 2026-06-28 — sau **Chat 13 Governance + Golden Dataset eval**: Migration 016 (`eval_runs`/`eval_results`) applied, seed 50 câu GMP (41 category), hợp đồng 4 tầng, GovernancePage JSX. **PASS.** *(F4 Frontend React parity 2026-06-28: 5 trang React + AssistantPanel + vá XSS. Platform Alignment 2026-06-27: Migration 015 + 9 WF + CI guard. Chat 11: WF-12 agentic, Migration 014. Chat 10: Citation Grounding PASS, Migration 013.)*
**Pages:** https://tienhoandhd-droid.github.io/Du_bao_thoi_tiet/ · **Repo:** `tienhoandhd-droid/Du_bao_thoi_tiet` (public)
**Local-dev:** **THUẦN GitHub web (bản free)** — không máy local, không dòng lệnh. Build TS chạy **trong GitHub Actions** (repo public → Actions không giới hạn phút; Pages free).

---

## 0. CÁCH DÙNG TÀI LIỆU NÀY
- **Đầu mỗi chat mới:** đính kèm file này; nơi nào mâu thuẫn thì **handoff thắng**. Mở chat **trong Project này**, nói rõ "đang ở Chat N, mục X".
- **Cuối mỗi chat:** cập nhật §2 (Nhật ký) + §3 (lỗi) + §5 (roadmap) → **xuất bản lại file này và THAY THẾ bản cũ** (giữ **1 file canon duy nhất**, bản mới nhất thắng).
- **File live là chân lý.** Mỗi chat hãy upload file thật (WF JSON, source) để Claude soi trực tiếp; đừng dựa vào trí nhớ AI.
- Mỗi đoạn chat làm **1 mục**. Ngôn ngữ: **tiếng Việt**.

---

## 1. TRẠNG THÁI TỔNG QUAN — ✅ MVP CHẠY ĐẦU-CUỐI (đang nâng cấp lên "trợ lý QA")

> Login (Supabase Auth) → AI Search gọi `rag-query` qua n8n → trả lời **có bảng trích dẫn** trỏ về SOP đã duyệt → Audit Trail ghi `user_email`. Đã xác nhận trên trình duyệt (Chat 06).

| Lớp | Trạng thái | Ghi chú |
|-----|-----------|---------|
| Database 001→010 + Migration 011 | ✅ Đã cài | `00_CHAY_TAT_CA_FULL_001-011.sql` |
| Verify JWT (RUNTIME) = **"Cách B"** | ✅ Đồng nhất 8 WF | HTTP `GET /auth/v1/user` + `apikey` anon; `onError=continueErrorOutput` → `Auth 401`. Params byte-identical, SHA-256 `d22a5154…cb27759`. |
| CORS webhook frontend gọi | ✅ `*` trong WF-01/02/06/07/08 | (WF-03/04/05/09 không browser gọi → không cần) |
| n8n — 8 WF Cách B + WF-08 | ✅ Import + Active | WF-01,08,11 ID thật; WF-02(__2_),06,07 + WF-03/04/05/09 relink khi import |
| Dữ liệu RAG (3 SOP mẫu) | ✅ Đã nạp + duyệt | SOP-CV/EQ/TM-001, mỗi cái 6 chunks, **AI Approved** (vi) |
| hybrid_search_v3 + chuỗi duyệt | ✅ Chạy thật (có trích dẫn) | Lọc qua `document_is_currently_valid` |
| **Frontend (Ice Crystal, vanilla module)** | ✅ Deploy + login + RAG có trích dẫn ĐẠT | `index.html`+`styles.css`+`js/config.js`+`js/app.js`; inject từ **Variables** |
| User admin | ✅ Đã tạo | `tienhoan.dhd@gmail.com`, Quản trị viên |
| CRAVE: Reranker + Query Expansion | ✅ Trong WF-02(__2_) | pool 24 → top 8, expansion VI+EN |
| **WF-11 Literature Search** | 🟡 File sẵn sàng (23/23), credential **ID thật** | webhook `literature-search`, 2 chế độ search/ingest, verify Cách B byte-identical. **WF-11 ĐÃ SẠCH** (OpenAl + ID thật). Chưa import. |
| **Spike GĐ0 — AI Agent native** | ✅ **ĐẠT** (Chat 08) | Agent + tool-calling chạy trong sandbox; trả `SPIKE OK - ket qua = 391` qua Calculator (Chat Model chạy 2×). **Crypto-block KHÔNG đụng đường agent.** |
| **Frontend TypeScript — nền móng** | ✅ **Deploy XANH trên Pages** (Chat 09) | Vite 5 + React 18 + TS + Tailwind 3 + shadcn foundation, đặt trong `app/`; build trong Actions; inject `VITE_*` OK (3 biến). |
| **Citation Grounding — Migration 013** | ✅ **PASS** (Chat 10, 2026-06-27) | `ai_query_sources` + `claim_text`/`grounded`/`citation_rank`; WF-02 lưu CTE; badge ✓/⚠ trên frontend vanilla. |
| **WF-12 — lõi trợ lý agentic** | ✅ **ĐÃ XÂY** (Chat 11) | AI Agent + Chat Model `OpenAl` + memory Postgres (Migration 014 `chat_memory`) + 3 tools governed qua `hybrid_search_v3`; webhook `/assistant-query`; v2 activeVersionId `DMcZCeYXTFRUyufV` thêm Embed Query. |
| **Platform Alignment — security hardening** | ✅ **PASS** (2026-06-27) | Migration 015: security_invoker 3 view, revoke RPC 11 hàm khỏi anon, search_path 17 hàm, append-only trigger; 9 WF re-point `bdttccztjtrcaztjgkot`; CI guard semantic + release manifest (git_sha `98ee969c`). |
| **F4 — Frontend React parity + AssistantPanel + vá XSS** | ✅ **PASS** (2026-06-28) | 5 trang React/TSX; `features/assistant/AssistantPanel.tsx` nối WF-12; badge grounded/ungrounded; XSS F4 vá (JSX escape mặc định, 0 `dangerouslySetInnerHTML`); build xanh 677ms; commit `5fc3a7b` lên `main`. |
| n8n WF-10 | 🔲 Kế hoạch (Chat 15) | Google Drive sync — kẹt ràng buộc 3-credential, xử lý lối vòng |
| Equipment-Aware + Glossary | 🔲 Kế hoạch (Chat 14) | Migration **017** (`equipment_code` + Glossary + sửa `'vi'` loại `'vi-en'`) |
| **Chat 13 — Governance + Golden Dataset eval** | ✅ **PASS** (2026-06-28) | Migration 016 applied; `eval_runs`/`eval_results` (RLS); seed **50 câu** GMP (41 category); `governance-contract.md` 4 tầng; GovernancePage JSX; `requirements_eval.txt` pin ragas/supabase/openai; git `703d889`. |

---

## 2. NHẬT KÝ THEO CHAT

### ✅ Chat 01 — Audit + Migration 011
DB 26 bảng/9 enum/~17 hàm/3 view khớp; 9/9 workflow parse OK. `011_fixes.sql` (idempotent, chặn trùng prompt active).

### ✅ Chat 02 — WF-02 → `hybrid_search_v3` + Query Expansion + Reranker
11 tham số (lọc governance/trust/quality trong DB) + Expansion VI+EN + Reranker (pool 24 → top 8). `RERANK_POOL=24`, `FINAL_TOP_N=8`, `MATCH_THRESHOLD=0.4`, `MIN_QUALITY=0.3`. ⚠ Có 2 bản file: `__1_` (cũ, OpenAL, **BỎ**) và `__2_` (mới, OpenAl, **GIỮ**).

### ✅ Chat 03 — Verify JWT (Plan A) + đóng gói
Plan A: JWKS offline trong Code node. ⚠ Chat 06 đổi sang **Cách B** (sandbox khoá crypto); Plan A xếp lại (giữ `verify_node_JWKS.js` tham khảo).

### ✅ Chat 04 — Cài thật Supabase + n8n · WF-01 · WF-08
Chạy SQL hợp nhất; import + Active. Xác nhận Supabase ký bất đối xứng. Vá JWT WF-01, verify WF-08 public. Credential OpenAI tên `OpenAl`.

### ✅ Chat 05 — Xác minh chuỗi duyệt + chuẩn bị nạp tài liệu
Trace SQL: duyệt set status+boolean cùng UPDATE; `hybrid_search_v3` lọc qua `document_is_currently_valid`. State-machine `indexed → reviewed → approved`. Chuẩn bị 3 SOP + RUNBOOK-CHAT05.

### ✅ Chat 06 — Frontend + Cách B + CORS + CHẠY ĐẦU-CUỐI
- Verify "Cách B": chuyển 8 WF từ JWKS-offline → HTTP `/auth/v1/user`. Baseline `d22a5154…`.
- CORS `allowedOrigins='*'` cho WF frontend gọi (01/02/06/07/08).
- Module hoá frontend: `index.html` + `styles.css` + `js/config.js` + `js/app.js`; `deploy.yml` inject.
- Gỡ lỗi: (F1) client đổi tên `sb` (tránh trùng `window.supabase`); (F2) `deploy.yml` đọc `vars.*` (không `secrets.*`); (F3) URL gốc (bỏ `/rest/v1/`).
- KẾT QUẢ: login OK; 3 SOP AI Approved; AI Search trả lời có trích dẫn; RAG trung thực.

### ✅ Chat 07 — WF-11 Literature Search (PubMed / Europe PMC)
- Rà schema → **KHÔNG cần migration 013** cho literature: lưu `documents`/`chunks` dùng `source_type='guideline'` + `source_category='literature'` (TEXT) + `source_organization` + `trust_level=2`.
- WF-11 = 1 webhook 2 chế độ (`search` công khai không lưu; `ingest` governance chỉ QA/Admin, nạp `status='indexed'` → phải qua chuỗi duyệt Chat 05).
- **Credential WF-11 SẠCH:** `OpenAl` + ID thật (`r5CC…`), Postgres `GMP-check` (`0WcJ…`) → import không relink. Validate 23/23.

### ✅ Chat 08 — TÁI ĐỊNH PHẠM VI + Spike GĐ0 *(chat này)*
**1. Tái định phạm vi:** từ *"RAG search MVP"* → *"trợ lý QA thẩm định dược"* trên **dashboard TypeScript lớn**; tìm kiếm chỉ là **một module** (assistant · documents · literature · validation · governance · audit · security). Thêm TypeScript để dựng hệ lớn.

**2. Đối chiếu trạng thái (sửa lệch câu mở đầu):** migration đã tới **011** (không phải 010); migration mới kế tiếp = **013** (012 để dành Plan B). Credential đúng là **`OpenAl`** (l thường), KHÔNG phải `OpenAL`.

**3. Audit credential trên file thật:** `OpenAl` + ID thật ở **WF-01/02(__2_)/08/11**. Nợ **`OpenAL`** (L hoa) chỉ còn ở **WF-03/04/05/09** + bản WF-02 cũ (`__1_`), và **chỉ là nhãn trên node `REPLACE`** (relink vẫn chọn `OpenAl`) → **không phải lỗi runtime**, chỉ là vệ sinh. *Đính chính ghi nhận cũ: WF-11 KHÔNG còn OpenAL — đã sạch.*

**4. Đánh giá 5 repo tham khảo:**
- **ÁP DỤNG:** `iamaber/medical-guideline-rag` (stack frontend TS Next/shadcn + pattern RAG guideline y tế) · node **AI Agent** của n8n.
- **NGUYÊN LÝ-ONLY:** `ashutoshrana/enterprise-rag-patterns` (defense-in-depth 4 tầng governance — *lib Python*, KHÔNG bê code vào n8n).
- **TRÁNH CÀI:** `lucasbrito-wdt/n8n-nodes-agent-kit` (dùng **OpenRouter = credential thứ 3** + community node trong sandbox khoá → **vi phạm ràng buộc**; chỉ mượn ý tưởng *skills-as-code*/guardrails bằng node native).
- **PHẦN LỚN NGOÀI PHẠM VI:** `tajo9128/BioDockify-Pharma-AI` (drug discovery: docking/QSAR/MD, Docker — không phải QA thẩm định).

**5. Spike GĐ0 — AI Agent native trong sandbox: ✅ ĐẠT (mức mạnh nhất).** File `SPIKE-AI-Agent.json` (Manual Trigger → AI Agent + OpenAI Chat Model `OpenAl` + Calculator). Chạy ra `SPIKE OK - ket qua = 391` **qua Calculator** (OpenAI Chat Model chạy **2×** = quyết gọi tool → soạn lại). Kết luận: **crypto-block KHÔNG ảnh hưởng đường AI Agent → GĐ2 đi ĐƯỜNG CHÍNH (AI Agent native + memory Postgres), KHÔNG cần fallback router thủ công.**

**6. Phát hiện lỗ XSS:** `app.js` hiện render `innerHTML` **không escape** (trừ `r.answer`) cho `document_code`, các trường audit, `source_type`… → **stored-XSS** nếu HTML lọt vào DB. **Vá khi port sang React (Chat 10).**

**7. Quyết định kiến trúc hệ mới:** (xem §4 mục 10–14).

**8. Local-dev = THUẦN GitHub web (free).** Build TS chạy trong Actions. **Cơ chế trung hoà:** Claude build-thử trong sandbox của mình trước, chỉ giao bản build xanh; người dùng upload + chạy Action + chụp màn hình.

**Sản phẩm Chat 08:** `SPIKE-AI-Agent.json` · `00-HANDOFF-CRAVE.md` · `KICKOFF-CHAT09.md`.

### ✅ Chat 09 — Dọn nợ credential + đường ống build TypeScript (nền móng)
**1. Dọn nợ credential (soi file thật):** WF-03/04/05/09 mỗi file đúng **1 nhãn `OpenAL`** trên node `REPLACE` → đổi `OpenAL`→`OpenAl` (giữ `id:"REPLACE"`), diff đúng 1 dòng/ file, JSON hợp lệ. **`OpenAL` = 0** ở cả 4. `WF-02 __1_` xác nhận **đã không còn** trong repo (chỉ còn `__2_`, sạch) → DoD "loại `__1_`" đạt ở cấp kho.

**2. Đường ống build TS — đặt trong THƯ MỤC CON `app/`:** để **giữ vanilla nguyên vẹn** ở gốc (vanilla chiếm `index.html` gốc), dự án Vite nằm trong `app/`; chỉ thay `deploy.yml`. Cây: `package.json` + `package-lock.json` (lockfileVersion 3, 187 gói) + `vite.config.ts` (`base:'/Du_bao_thoi_tiet/'`, alias `@`→`src`) + `tsconfig.json` + `tailwind.config.ts` (token **Ice Crystal** qua biến CSS dạng channel `H S% L%` + `/<alpha-value>`) + `postcss.config.js` + `components.json` + `.gitignore` + `src/{main.tsx, App.tsx, index.css, vite-env.d.ts, lib/utils.ts}`. App "hello dashboard" đọc/validate `import.meta.env.VITE_*` (OK / RỖNG / PLACEHOLDER, che anon key).

**3. `deploy.yml` mới (Vite, subfolder):** checkout → guard Variables (rỗng/placeholder) → setup-node **22** (`cache-dependency-path: app/package-lock.json`) → `npm ci` (working-directory `app`) → `npm run build` (`tsc` strict + `vite build`) inject `VITE_*` từ `vars.*` → guard `dist` (không placeholder + có URL thật) → upload `app/dist` → deploy. Giữ đúng **3 Variables cũ**, anon-key-only.

**4. Nghiệm thu ĐẠT:** build-thử sandbox xanh (34 modules, CSS 9.76kB, JS ~166kB); base/asset = `/Du_bao_thoi_tiet/…`; inject xác nhận (3 giá trị bake vào `dist`, 0 placeholder). **Action #18 Success (23s)**; trang Pages hiển thị hello dashboard với **3 biến OK** (Supabase URL + anon key 208 ký tự + webhook `n8n.cpc1hn.com/webhook`).
> *Quyết định:* URL live tạm hiển thị hello dashboard; vanilla source ở gốc **nguyên vẹn**, quay lui = revert 1 file `deploy.yml`. Cảnh báo "Node.js 20 deprecated → 24" là runtime của *bản action* (checkout@v4…), KHÔNG đụng build.

**Sản phẩm Chat 09:** `app/` (cây Vite, đã build-thử xanh) · `deploy.yml` (Vite, subfolder) · WF-03/04/05/09 (sạch `OpenAl`) · `00-HANDOFF-CRAVE.md` · `KICKOFF-CHAT10.md`.

### ✅ Chat 10 — Citation Grounding (Migration 013) — 2026-06-27 — **PASS**

**1. Migration 013** (`supabase/migrations/013_citation_grounding.sql`): thêm 3 cột vào `ai_query_sources` (`claim_text TEXT`, `grounded BOOLEAN NOT NULL DEFAULT false`, `citation_rank INT`); thêm 3 constraint + 3 index + INSERT policy RLS; rollback `013_down.sql` dùng comment `CRAVE-013` để tránh drop cột tiền-migration (idempotent).

**2. Fix JWT Verify URL WF-02:** URL cũ trỏ project `xrpnlpfcoarouoqkhgfp` (sai) → sửa thành project hiện tại `bdttccztjtrcaztjgkot`. Params vẫn byte-identical Cách B.

**3. WF-02 Format Response — lưu citation grounding:** viết lại `save_sql` thành CTE đơn; bổ sung `INSERT INTO ai_query_sources` với `chunk_id`, `grounded`, `citation_rank` cho mỗi chunk trả về từ `hybrid_search_v3`.

**4. Frontend vanilla (js/app.js + styles.css):** bảng nguồn thêm cột "Trạng thái"; badge **✓ Xác minh** (xanh) / **⚠ Chưa xác minh** (vàng) theo trường `grounded` từ API. F4 (XSS) chưa vá — hoãn sang Chat 12 (khi port React).

**Sản phẩm Chat 10:** `supabase/migrations/013_citation_grounding.sql` · `013_down.sql` · `js/app.js` (badge) · `styles.css` · `00-HANDOFF-CRAVE.md` (bản này).

### ✅ Chat 11 — WF-12 lõi trợ lý agentic (Migration 014) — 2026-06-27

**1. Migration 014** (`supabase/migrations/014_chat_memory.sql`): bảng `chat_memory` (user_id, session_id, role, content, metadata, created_at); RLS chỉ `authenticated`; index `idx_chat_memory_user_session_created_at`. Rollback `014_down.sql`.

**2. WF-12 TKTL — AI Agent native:** AI Agent node + Chat Model `OpenAl` (gpt-4o-mini) + 3 tools governed qua `hybrid_search_v3` (`rag_search`, `literature_lookup`, `calc`); memory Postgres (`GMP-check`); verify Cách B byte-identical; audit append-only. Webhook POST `/assistant-query`. WF-12 v2 thêm node Embed Query `text-embedding-3-small`; activeVersionId `DMcZCeYXTFRUyufV`.

**Sản phẩm Chat 11:** `TKTL WF-12` (n8n, published) · `supabase/migrations/014_chat_memory.sql` · `014_down.sql`.

### ✅ Chat 13 — Governance tường minh + Golden Dataset eval — 2026-06-28 — PASS

**Migration 016** (`supabase/migrations/016_eval_harness.sql`): bảng `eval_runs` (id, run_at, model_tag, n_questions, score_mean, score_min, passed, notes) + `eval_results` (id, run_id→eval_runs, question_id→golden_questions, answer, score_faithfulness, score_relevancy, score_context_recall, grounded_pct, passed, raw_json); RLS `authenticated` SELECT+INSERT; index `idx_eval_results_run_id` + `idx_eval_runs_run_at`. Rollback `016_down.sql`. Idempotent (DO block + IF NOT EXISTS + policy guard).

**Seed golden_questions:** `scripts/seed_golden_questions.sql` bổ sung 43 câu → tổng **50 câu GMP** (41 category: sop_control, batch_records, deviations, CAPA, OOS, stability, v.v.). Idempotency: advisory lock + NOT EXISTS theo nội dung câu hỏi.

**Eval harness:** `scripts/run_eval.py` — Ragas 3 metric (faithfulness, answer_relevancy, context_recall) + grounded_pct; đọc keys từ env (SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, WEBHOOK_BASE); ghi kết quả vào `eval_runs`/`eval_results`. `requirements_eval.txt` pin `ragas>=0.1,<0.2`, `supabase>=2.0,<3.0`, `openai>=1.0,<2.0`.

**Governance-contract.md:** 4 tầng (Input 500 ký tự + SQL injection guard → Retrieval hybrid_search_v3 → Generation constraint + disclaimer → Output grounded_pct≥0.60 + confidence≥MEDIUM). Ngưỡng eval 0.90 ≠ ngưỡng grounding 0.60.

**GovernancePage:** tích hợp vào Security panel (`App.tsx` dòng 1476–1507); JSX thuần, 0 `dangerouslySetInnerHTML`. `GOVERNANCE_LAYERS` const array 4 tầng.

**Sản phẩm Chat 13:** `supabase/migrations/016_eval_harness.sql` + `016_down.sql` · `scripts/seed_golden_questions.sql` · `scripts/run_eval.py` · `scripts/requirements_eval.txt` · `docs/governance-contract.md` · `app/src/App.tsx` (GovernancePage). Git `703d889` → `main`.

### ✅ Platform Alignment — security hardening — 2026-06-27 — PASS

**PHA 1A — Migration 015** (`supabase/migrations/015_platform_security_hardening.sql`): (1) `security_invoker=true` cho 3 view tài liệu; (2) revoke EXECUTE 11 RPC từ `public`/`anon`/`authenticated`, chỉ `service_role`; (3) khóa `search_path` 17 hàm; (4) trigger append-only `crave_block_append_only_mutation` cho `audit_log` + `chat_memory`; (5) RLS tường minh cả hai bảng. Rollback `015_down.sql`.

**PHA 1B — n8n TKTL N8N-01→08 (9 workflow):** re-point toàn bộ sang project `bdttccztjtrcaztjgkot` + anon key mới; parameterized SQL; WF-12 v2 Embed Query. activeVersionIds: WF-01=`2c707741`, WF-02=`767e4afb`, WF-03=`66c5e44a`, WF-04=`fb751091`, WF-05=`1a3919c5`, WF-06=`f7b7ee5a`, WF-07=`8f2d714c`, WF-09=`c03ee46b`, WF-11=`bad508fe`, WF-12=`8d6c7110`.

**PHA 1C — deploy.yml CI guard semantic + release manifest:** Guard 1: SUPABASE_URL chứa `bdttccztjtrcaztjgkot`, decode JWT payload kiểm `ref`, cấm `xrpnlpfcoarouoqkhgfp`. Guard 2: dist không chứa ref cũ. Manifest `dist/release-manifest.json` (git_sha, migration_version=015, 10 WF activeVersionIds, supabase_project). Action xanh (git_sha `98ee969c`).

**Sản phẩm Platform Alignment:** `supabase/migrations/015_platform_security_hardening.sql` + `015_down.sql` · `claude-review/platform-alignment-2026-06-27/` · `.github/workflows/deploy.yml` (CI guard + manifest).

---

## 3. LỖI & TRẠNG THÁI

| # | Lỗi | Mức | Trạng thái |
|---|-----|-----|-----------|
| 1 | JWT chỉ base64-decode, không verify | 🔴 | ✅ ĐÃ SỬA; runtime = **Cách B** |
| 2 | Prompt `rag_query` v1.0+v2.0 cùng active | 🟠 | ✅ ĐÃ SỬA (011) |
| 3 | WF-02 gọi `hybrid_search` v1 thiếu governance | 🟠 | ✅ ĐÃ SỬA (v3) |
| 4 | `roles` chưa bật RLS | 🟡 | ✅ ĐÃ SỬA (011) |
| F1 | Frontend nút "chết im" (trùng tên `supabase`) | 🔴 | ✅ ĐÃ SỬA (client → `sb`) |
| F2 | Cấu hình rỗng (Variables vs Secrets) | 🔴 | ✅ ĐÃ SỬA (deploy.yml dùng `vars.*`) |
| F3 | SUPABASE_URL thừa `/rest/v1/` | 🟠 | ✅ ĐÃ SỬA (URL gốc) |
| **F4** | **`app.js` render `innerHTML` không escape (trừ `r.answer`) → stored-XSS** | 🟠 | 🔲 **Vá ở hạng mục kế** (Frontend React parity; React escape mặc định) |
| **SB-08** | **Leaked-password protection** (Supabase Dashboard) | 🟡 | 🔲 Cấu hình thủ công; chờ |

**HOÃN:** `hybrid_search_v3` lọc `'vi'` loại `'vi-en'` — sửa ở **migration 017+ (Chat 14)**; không cắn ở chế độ `'any'` mặc định.
**HOÃN (Chat 07):** WF-11 nạp lại cùng `pmid`/`doi` đụng `UNIQUE(...)` → xử lý `ON CONFLICT`/versioning sau.
**Credential (ĐÃ DỌN ở Chat 09):** OpenAI = **`OpenAl`** (l thường, ID `r5CCCyYKeJDjnJ0A`). Nợ `OpenAL` đã **hết**. `WF-02 __1_` đã loại.
**Cảnh báo lành tính (Chat 09):** Action #18 báo "Node.js 20 deprecated → 24" — deprecation runtime action, KHÔNG đụng build Node 22.
**Migration (thực tế đã áp):** 013 = citation grounding ✅ · 014 = chat_memory ✅ · 015 = security hardening ✅ → **số trống kế tiếp = 016**; equipment+glossary = **017+** (Chat 14).

---

## 4. QUYẾT ĐỊNH KỸ THUẬT
1. **Verify JWT (RUNTIME) = Cách B remote.** HTTP `/auth/v1/user` + `apikey` anon; `onError=continueErrorOutput` → `Auth 401`. Baseline `d22a5154…`.
2. **Plan A (JWKS offline):** xếp lại. **Plan B (HS256):** không dùng; số 012 để dành.
3. **WF-02 v1→v3.** Migration mới = **014** kế tiếp (013 đã dùng chat_memory → citation grounding).
4. **Credential:** OpenAI = **`OpenAl`** (ID `r5CCCyYKeJDjnJ0A`); Postgres `GMP-check` (ID `0WcJFXEhwLXQhJmn`). WF-01,08,11 mang ID thật; WF-02(__2_),06,07 + WF-03/04/05/09 dùng `REPLACE` → relink khi import.
5. **CORS:** `allowedOrigins='*'` ở node Webhook cho WF frontend gọi.
6. **Frontend (vanilla cũ):** client tên **`sb`** (tránh trùng `window.supabase`).
7. **Cấu hình frontend = GitHub REPOSITORY VARIABLES** (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `WEBHOOK_BASE`).
8. **SUPABASE_URL = URL GỐC** `https://bdttccztjtrcaztjgkot.supabase.co` (project hiện tại). **WEBHOOK_BASE** = `https://n8n.cpc1hn.com/webhook`. *(Project cũ `xrpnlpfcoarouoqkhgfp` = CẤM; CI guard cũng chặn.)*
9. **(Chat 07) Literature KHÔNG cần migration 013.** Map vào schema sẵn có bằng cột TEXT.
10. **(Chat 08) Tái định phạm vi:** "RAG search MVP" → **"trợ lý QA thẩm định"** trên dashboard lớn; search là 1 module.
11. **(Chat 08) Frontend TS = Vite + React + TypeScript + Tailwind + shadcn/ui, STATIC** (KHÔNG Next.js full vì Pages tĩnh). `base:'/Du_bao_thoi_tiet/'`. **Build trong GitHub Actions** (inject `VITE_*` từ `vars.*`, vẫn **anon-key-only**). Local-dev **thuần GitHub web (free)**.
12. **(Chat 08) Backend agentic = node AI Agent NATIVE** (spike GĐ0 ĐẠT — agent + tool-calling chạy trong sandbox, crypto-block không đụng). **Memory đặt ở Postgres** (`GMP-check`) → **không cần credential thứ 3**. Không cài community node.
13. **(Chat 08) Cổng governance khi lên agentic:** MỌI tool truy hồi **BẮT BUỘC qua `hybrid_search_v3`** — không node nào `SELECT` thô bảng `documents`. Mỗi lượt trợ lý ghi **audit append-only**.
14. **(Chat 08) Repo:** áp dụng `medical-guideline-rag` (stack TS) + AI Agent n8n; nguyên-lý-only `enterprise-rag-patterns` (4 tầng defense-in-depth); **tránh cài** `n8n-nodes-agent-kit` (OpenRouter=cred thứ 3); `BioDockify` ngoài phạm vi.
15. **(Chat 09) Dự án Vite đặt trong `app/`** (KHÔNG ghi đè gốc) để giữ app vanilla nguyên vẹn; `deploy.yml` dùng `working-directory: app`, build `app/` và deploy `app/dist`. URL live tạm hiển thị hello dashboard tới khi Chat 10 parity; quay lui = revert 1 file `deploy.yml`.
16. **(Chat 09) Bộ phiên bản TS chốt:** Vite **5** + React **18** + TypeScript **5** + Tailwind **3** (config `.ts`; token qua biến CSS dạng channel `H S% L%` + `/<alpha-value>` để opacity chạy + tương thích shadcn) + shadcn foundation (`components.json`, `lib/utils.ts` `cn()`). CI **Node 22** (khớp bản build-thử của Claude). `package.json`/`lock` **phát theo cặp**, không sửa tay.
17. **(Chat 10) Citation Grounding:** Migration 013 thêm `claim_text`/`grounded`/`citation_rank` vào `ai_query_sources`; WF-02 lưu citation qua CTE đơn; badge ✓/⚠ frontend vanilla. JWT Verify URL WF-02 fix sang project `bdttccztjtrcaztjgkot`. F4 (XSS) hoãn → hạng mục kế (React parity).
18. **(Chuỗi migration thực tế):** 013 = citation grounding ✅ → 014 = chat_memory ✅ → 015 = security hardening ✅ → **016 = số trống kế tiếp** → 017+ = equipment+glossary (Chat 14).
19. **(Platform Alignment 2026-06-27) Security hardening:** Migration 015; 11 RPC SECURITY DEFINER bị revoke từ anon; trigger append-only `audit_log`+`chat_memory`; CI guard semantic cấm project cũ `xrpnlpfcoarouoqkhgfp`. Baseline CI: git_sha `98ee969c`, manifest `migration_version=015`.
20. **(Platform Alignment 2026-06-27) Quy trình commit:** **Claude Code commit + push thẳng `main`** (chỉ hỏi xác nhận qua chat trước khi push). Codex viết code → Claude Code check/sửa → commit + push. KHÔNG còn quy trình "user dán web" (ngoại trừ upload file n8n JSON lên Supabase/n8n — các thao tác đó vẫn cần anh làm thủ công).

---

## 5. ROADMAP

**Đã xong:** ✅ 01 Audit+011 · ✅ 02 WF-02 v3 · ✅ 03 Verify JWT · ✅ 04 Cài thật+WF-01/08 · ✅ 05 Chuỗi duyệt+SOP · ✅ 06 Frontend+Cách B+CORS (chạy đầu-cuối) · ✅ 07 WF-11 Literature · ✅ 08 Tái định phạm vi + spike GĐ0 ĐẠT · ✅ 09 Dọn nợ credential + đường ống build TS (hello dashboard XANH) · ✅ **10 Citation Grounding — Migration 013 + WF-02 fix + badge frontend (PASS)** · ✅ **Chat 11 — WF-12 agentic + Migration 014** · ✅ **Platform Alignment — Migration 015 + 9 WF + CI guard/manifest (PASS 2026-06-27)** · ✅ **F4 — Frontend React parity + AssistantPanel + vá XSS (PASS 2026-06-28)**

**Kế hoạch chat hệ mới (mỗi chat = 1 mục, validate được, không phá MVP):**
- **✅ Chat 09 — Dọn nợ + đường ống build TS.** *(ĐẠT.)*
- **✅ Chat 10 — Citation Grounding.** Migration 013; WF-02 CTE save + fix JWT Verify URL; badge ✓/⚠. *(PASS.)*
- **✅ Chat 11 — WF-12 lõi trợ lý agentic.** AI Agent native + Memory Postgres (Migration 014 `chat_memory`) + 3 tools governed qua `hybrid_search_v3` + verify Cách B + audit. Webhook `/assistant-query`. *(ĐÃ XÂY.)*
- **✅ Platform Alignment — security hardening (2026-06-27).** Migration 015 (security_invoker + revoke RPC + search_path + append-only); 9 WF TKTL re-point project mới; CI guard semantic + release manifest (git_sha `98ee969c`). *(PASS.)*
- **✅ F4 — Frontend React parity + AssistantPanel + vá XSS (2026-06-28).** Port 5 trang sang React; `features/assistant/AssistantPanel.tsx` nối WF-12; badge grounded/ungrounded; XSS F4 vá; build xanh; commit `5fc3a7b`. *(PASS.)*
- **✅ Chat 13 — Governance tường minh + Golden Dataset eval (2026-06-28).** Migration 016 (`eval_runs`/`eval_results`, RLS, index); seed 50 câu GMP (41 category); `governance-contract.md` 4 tầng + disclaimer; GovernancePage JSX thuần; `run_eval.py` Ragas đọc key từ env; `requirements_eval.txt` pin version; git `703d889`. *(PASS.)*
- **🔲 Chat 14 — Equipment-Aware + Glossary + công cụ thẩm định.** Migration **017** (`equipment_code` + Glossary + sửa `'vi'` loại `'vi-en'`); WF-03/04/05 lên `features/validation/`.
- **🔲 Chat 15 — Nguồn dữ liệu + skills-as-code + đóng gói.** WF-10 Drive (lối vòng / hoãn có ghi nhận); prompt versioned ở Postgres; runbook + hồi quy cuối.

*Linh hoạt:* 09–10 là track frontend, 11–15 nghiêng backend/nghiệp vụ (gần độc lập). Chat ngắn có thể gộp (11+12, hoặc gập 13 vào 14).
**HOÃN dài hạn:** Knowledge Graph, Redis Cache, tách WF-02 thành 5 workflow.

---

## 6. ⚙ LƯU Ý VẬN HÀNH

### 6.1 Thêm workflow/webhook MỚI — KHÔNG ảnh hưởng đăng nhập
- Login = Supabase Auth, độc lập n8n. `WEBHOOK_BASE` là URL gốc → webhook mới gọi bằng `WEBHOOK_BASE + '/<path>'`, KHÔNG đổi Variable.
- Nếu webhook mới **frontend gọi**: (1) CORS `*` vào node Webhook; (2) thêm endpoint trong `lib/api.ts` (hệ mới) / `js/app.js` (cũ) rồi deploy lại; (3) nếu cần auth: clone node verify Cách B byte-identical (`d22a5154…`).

### 6.2 Khi đổi key/URL/webhook
- Sửa **Settings ▸ Secrets and variables ▸ Actions ▸ tab Variables** → chạy lại Action → xoá cache (`?v=...`). Inject xảy ra lúc build.

### 6.3 Nạp thêm tài liệu
- `RUNBOOK-CHAT05.md`: ingest → review → approve (2 lần approve, vai trò QA Manager/Admin). Chỉ `approved_for_ai_use=true` vào RAG.

### 6.4 Quy trình làm việc hệ mới (Claude Code commit thẳng main)
- **Quy trình từ Platform Alignment trở đi:** Codex viết code → Claude Code check/sửa → **commit + push thẳng `origin/main`** (hỏi xác nhận qua chat trước khi push, không cần user dán web).
- **KHÔNG sửa `package.json`/`package-lock.json` bằng tay** — Claude phát lại **cả cặp** khi đổi deps.
- Thao tác cần làm thủ công (ngoài git): upload WF JSON lên n8n, apply migration lên Supabase (Claude Code xin "ĐỒNG Ý APPLY" qua chat trước), thiết lập Variables Actions.
- Báo lỗi bằng **ảnh / log nguyên văn** (đọc trực tiếp, không đoán).

---

## 7. RÀNG BUỘC BẤT BIẾN
| Ràng buộc | Yêu cầu |
|-----------|---------|
| Credentials n8n | Chỉ `GMP-check` + `OpenAl`. KHÔNG Variables n8n. Memory agentic đặt ở Postgres (không cần cred thứ 3) |
| Deploy frontend | GitHub web (upload + Actions), **không dòng lệnh**. Build TS chạy trong Actions (repo public → không giới hạn phút) |
| Local-dev | **Thuần GitHub web (free)** — không máy local. Claude build-thử thay, chỉ giao bản xanh |
| Bảo mật key | Không key bí mật (service-role/OpenAI/JWT-secret) trong frontend/source; anon key được phép |
| Xác thực | Verify token thật — Cách B (HTTP `/auth/v1/user`, verify ES256) |
| OpenAI runtime | Chỉ từ n8n backend |
| AI sources | Chỉ `approved_for_ai_use`; **mọi tool agent qua `hybrid_search_v3`** (không SELECT thô) |
| Audit log | Append-only (INSERT); mỗi lượt trợ lý đều ghi |
| Migration | 001→010→011 ✅ → 012 (Plan B, để dành) → **013 citation ✅** → **014 chat_memory ✅** → **015 security hardening ✅** → **016 = số trống kế tiếp** → 017+ equipment+glossary |
| Ngôn ngữ | Tiếng Việt |

---

## 8. QUY ƯỚC FILE
- Migration đặt số tăng dần; chạy nối tiếp; idempotent.
- **Frontend vanilla cũ:** `index.html` + `styles.css` + `js/config.js` + `js/app.js` + `deploy.yml` (sed inject `vars.*`). *(Giữ sống tới khi TS đạt parity ở hạng mục kế.)*
- **Frontend hệ mới (TS) — trong THƯ MỤC CON `app/`:** `app/{package.json, package-lock.json (lockfileVersion 3, 187 gói), vite.config.ts (base '/Du_bao_thoi_tiet/', alias @→src), tsconfig.json, tailwind.config.ts, postcss.config.js, components.json, .gitignore, src/(main.tsx, App.tsx, index.css, vite-env.d.ts, lib/utils.ts; sẽ thêm types/, hooks/, components/, features/ ở Chat 10)}` + `.github/workflows/deploy.yml` (working-directory `app`; npm ci → vite build → deploy **`app/dist`**, inject `VITE_*`). **Không sửa package.json/lock bằng tay.** App vanilla ở GỐC giữ nguyên.
- **Bộ workflow:** `WF-01,02(__2_),06,07,08` (Cách B + CORS) + `WF-03,04,05,09` (Cách B) + `WF-11` (ID thật). Bỏ WF-02(__1_).
- **WF-12** (Chat 11, ĐÃ XÂY): AI Agent + tools governed + memory Postgres (Migration **014** bảng `chat_memory`) + verify Cách B + audit. Webhook `/assistant-query`. v2 activeVersionId `DMcZCeYXTFRUyufV`.
- **Params verify byte-identical; baseline `d22a5154…cb27759`.**
- **Repo GitHub Pages chỉ chứa frontend.** Workflow ở n8n, SQL ở Supabase — không đẩy lên GitHub.

*Nguồn sự thật chung. Xuất bản lại & thay thế sau mỗi chat.*
