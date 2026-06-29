# System Check S1 — 2026-06-29

**Chu kỳ:** 1 — Chat 01–05
**Owner:** Claude Code / Codex GPT
**Main được kiểm:** `7fd1db52cf01520fde77001afe17809e8447bd44`
**Quyết định:** **HOLD — CHƯA GO CYCLE 2**

## Tóm tắt

Cycle 1 đã đưa snapshot, Supabase source map, 14 workflow TKTL đã redaction và
release guardrail lên `main`. GitHub release guard, n8n source/live reconciliation,
manifest hash và secret scan đều PASS. Tuy nhiên S1 phát hiện ba blocker không thể
hạ xuống caveat: required TypeScript check không được tạo cho PR ngoài `app/**` và
lần chạy thực tế gần nhất của check này đang FAIL; migration/rollback chưa đủ để
restore theo convention đích; Supabase live RLS/grants/function signatures không
thể tái xác minh trong phiên vì không có Supabase MCP khả dụng.

S1 chỉ đọc GitHub, n8n và source local; không apply SQL, không execute/publish n8n,
không đổi GitHub settings. File này là artifact duy nhất được tạo bởi System Check.

## Kết luận riêng về required `TypeScript Build & Lint`

### Nguyên nhân check không chạy trên PR #3

Branch protection của `main` yêu cầu context chính xác `TypeScript Build & Lint`
với strict mode. Tuy nhiên `.github/workflows/ci.yml` chỉ nhận sự kiện khi diff
chạm `app/**` hoặc chính `.github/workflows/ci.yml`. PR #3 chỉ chứa baseline,
Supabase/n8n source và scaffold/guardrail nên GitHub không tạo check run; trạng
thái required check bị treo thay vì PASS/skip.

### Lỗi thứ hai: check hiện không xanh khi được kích hoạt

Run gần nhất `28329680736` trên commit `3b31362` cho thấy:

- Variables bắt buộc: PASS.
- `npm ci`: PASS, nhưng báo 1 moderate + 1 high dependency vulnerability.
- `npx tsc --noEmit`: PASS.
- `npm run build`: PASS; Vite build hoàn tất.
- Bước `Kiểm tra output không chứa placeholder`: **FAIL**.

Nguyên nhân là lệnh quét generic `PLACEHOLDER` trên toàn bundle. Frontend có chủ
ý dùng `PLACEHOLDER` làm tên constant/trạng thái và thông báo người dùng trong
`app/src/lib/env.ts` và `app/src/App.tsx`; do đó scanner tự đánh dấu code hợp lệ.
Lệnh `grep` hiện còn in nguyên dòng bundle khớp ra log, gây log rất lớn và trái
với nguyên tắc scanner không tiết lộ matched material.

### Sửa đề xuất — chưa thực hiện trong S1

1. Bỏ `paths` ở trigger `pull_request` để required check luôn được tạo cho mọi PR
   vào `main`; có thể giữ tối ưu ở job-level sau khi đã bảo đảm context luôn tồn tại.
2. Thay grep generic bằng rule unresolved sentinel cụ thể, ví dụ
   `__[A-Z0-9_]+__`, `YOUR_SUPABASE_URL`, `YOUR_SUPABASE_ANON_KEY`, `changeme`
   và `TODO_KEY`; không cấm từ nghiệp vụ `PLACEHOLDER` chung chung.
3. Dùng chế độ quiet và chỉ báo rule/path, không in nội dung bundle khớp.
4. Chạy lại TypeScript check trên `main` và yêu cầu một run `SUCCESS` trước GO.
5. Cân nhắc thêm `Static manifest guard (synthetic fixture)` vào required checks.
6. Quyết định rõ policy single-owner: hoặc bật `enforce_admins`, hoặc ghi controlled
   admin-bypass procedure; hiện PR #3 được admin merge vì không có reviewer thứ hai.

## Kết quả 11 mục

| # | Mục kiểm | Kết quả | Bằng chứng và nhận định |
|---:|---|---|---|
| 1 | Issue/branch/commit/PR/merge/release status | **FAIL** | PR #3 đã merge vào `main` tại `7fd1db5`, nhánh Chat 04–05 đã xóa. Tuy nhiên Issue #2 vẫn OPEN; `change-register.md` vẫn ghi Chat 03/04 là kế hoạch; `kehoach.md §14.2` vẫn ghi Chat 01–05 là kế hoạch. PR dùng admin bypass vì review required không thể được thỏa bởi cùng owner. |
| 2 | Test/lint/build/harness của Chat 01–05 | **FAIL** | Release guard run `28342566501` trên merge commit PASS; Chat 05 unit test 8/8 PASS; n8n JSON/hash PASS; FTS eval run `28329778248` PASS. Nhưng required TypeScript run gần nhất `28329680736` kết luận FAILURE ở scanner placeholder, dù TSC và Vite build bên trong run đã PASS. Không có successful TypeScript check trên current `main`. |
| 3 | Secret scan toàn diff/source | **PASS** | `scripts/scan_repository_secrets.py app docs eval n8n prompts scripts supabase` PASS; validator test chứng minh secret giả bị chặn mà không echo giá trị. 14 n8n export đã redaction; credential names chỉ gồm `GMP-check`, `OpenAl`, `CRAVE-Google-Workspace`, `CRAVE-Tavily`, đều thuộc whitelist hiện hành. |
| 4 | Migration source + rollback cùng số/tên vs live | **FAIL** | Source map ghi 001–011 baseline-only; 016 missing evidence; tên 021c không byte-identical. Rollback 013–021 nằm theo convention cũ trong `supabase/migrations/` với tên `0NN_down.sql`; 021b/021c/021d không có rollback riêng. Chỉ 022 có rollback ở `supabase/rollbacks/`, nhưng rollback là drop signature + manual restore vì thiếu old definition. Theo reviewer rule, thiếu rollback = HOLD. |
| 5 | Workflow GitHub vs n8n live | **PASS** | MCP trả đúng 14 workflow TKTL, tất cả active. 14/14 ID, `versionId`, `activeVersionId` và node count khớp `n8n/release-manifest.json`; không workflow nào còn draft/active drift. WF-14 live/version `4f2f07d4-da78-4196-a70a-80510ac6fbd2` khớp source; 14/14 SHA-256 file PASS. |
| 6 | Prompt version/hash vs workflow/log/eval/manifest | **N/A với caveat** | `prompts/` hiện chỉ là scaffold README; không có prompt production `vN.md`, nên Cycle 1 không có prompt content để hash/activate. System release manifest thật chưa tồn tại; chỉ có n8n reconciliation manifest và synthetic fixture. Không được coi fixture là release evidence production. |
| 7 | Retrieval/prompt/workflow/model qua eval gate | **PASS với caveat** | Không có prompt/model/retrieval logic mới trong Chat 01–05. FTS eval gần nhất: run ID `dce0b26a-989a-4061-8ea6-dc215a626f95`, 58/58 câu có source, Hit@1 81.03%, Hit@3 94.83%, Hit@5 96.55% ≥80%, MRR 0.8807, PASS. WF-14 remediation có positive/negative JWT/Tavily test trong provenance, nhưng đây không phải full RAG eval. |
| 8 | Frontend/CI/manifest vs GitHub state | **FAIL** | `app/` không bị move và không đổi trong Cycle 1. Release guard trên merge commit PASS. Nhưng required TypeScript check bị trigger path loại bỏ khỏi PR và run gần nhất FAIL bởi scanner false-positive. PR #3 chỉ merge qua admin override. Chưa có system `release-manifest.json` thật chứa Git/migration/WF/prompt/model/dataset. |
| 9 | RLS/grants/audit/JWT/hybrid search/citation/no-source | **NOT FULLY VERIFIED — FAIL GATE** | Source scan không thấy UPDATE/DELETE/TRUNCATE `audit_log`; baseline ghi `audit_log` bật RLS; 13 workflow cần auth có `/auth/v1/user` và `continueErrorOutput`, WF-08 N/A; AI retrieval WF-02/WF-12/WF-13 gọi `hybrid_search_v3`; credential whitelist PASS. Tuy nhiên phiên S1 không có Supabase MCP nên không thể tái kiểm `pg_policies`, grants, function owner/security definer, live migration list hoặc audit immutability. WF-06 còn dựng SQL tìm documents từ request bằng string interpolation và cần security review dù đây là user document search, không phải AI retrieval. |
| 10 | Tổng hợp drift/regression/conflict và GO/HOLD | **HOLD** | Có blocker CI, rollback/restore và thiếu live Supabase verification. Governance register/Issue còn stale. Không được bắt đầu migration 023 như một release bình thường cho tới khi điều kiện GO bên dưới được đóng hoặc có change-control chấp thuận remediation lane riêng. |
| 11 | Source-runtime drift mới | **PARTIAL / HOLD** | n8n không có drift mới: 14/14 active/source match. Supabase 022 source được phục hồi từ evidence nhưng live chưa re-read trong S1; 016/021 mapping và rollback 021b–d vẫn là drift đã biết. Prompt production chưa tồn tại nên không có active/source comparison. GitHub `main` và local tree khớp `7fd1db5`. |

## Secret scan

**Kết quả:** PASS.

- Quét `app`, `docs`, `eval`, `n8n`, `prompts`, `scripts`, `supabase`.
- Không phát hiện Tavily/OpenAI key, JWT/service key dài hoặc assigned secret.
- Không in matched value.
- Các file ngoài Git `.DS_Store`, `.codex/`, `n8n/.DS_Store`, `supabase/data/`
  không thuộc merge commit và không được dùng làm evidence.

## Source-runtime drift

| Thành phần | Source `main` | Live/evidence | Kết luận |
|---|---|---|---|
| GitHub | `main` = `7fd1db5`; PR #3 merged | Remote `main` cùng SHA; release guard PASS | Khớp, nhưng TypeScript required check/gate lỗi |
| Supabase migrations | 013–022 source; baseline 001–012; 022 canonical source+down | Snapshot Chat 03 ghi live tới 022 | Chưa tái verify live; 016/021 và rollback gaps còn mở |
| n8n | 14 JSON + manifest SHA | MCP: 14 active, ID/version/node count khớp | PASS, không draft/active drift |
| WF-14 | Credential reference `CRAVE-Tavily`, JWT error branch, active version trong manifest | MCP active version `4f2f07d4-da78-4196-a70a-80510ac6fbd2` | PASS |
| Prompt | Chỉ scaffold README | Không có prompt production version | N/A; chưa đủ cho system release manifest |
| Model/dataset | Contract + synthetic fixture; eval harness hiện hữu | FTS eval PASS 58/58 | Fixture không phải release evidence production |

## [x] Đã hoàn thành

- Cycle 1 source package đã merge vào `main` qua PR #3.
- Local/remote `main` cùng merge commit `7fd1db5`.
- 14/14 workflow TKTL có JSON canon, redaction, provenance và SHA-256.
- 14/14 workflow live activeVersion khớp manifest; WF-14 không còn drift.
- Tavily literal cũ đã revoke theo provenance Chat 04; binding dùng credential whitelist.
- Release manifest validator và 8 positive/negative test PASS.
- Release guard GitHub Action PASS trên merge commit.
- Secret scan toàn source PASS.
- FTS eval 58 câu: Hit@5 96.55%, PASS.

## [ ] Kế hoạch remediation trước GO

1. **CI owner:** sửa trigger required check và scanner false-positive; chạy TypeScript
   check xanh trên current `main`; đề xuất đưa release guard vào branch protection.
2. **Database owner + Claude read-only MCP:** tái đọc live migration list, function
   signatures, policies, grants, RLS và audit controls của project
   `bdttccztjtrcaztjgkot`.
3. **Database/change-control owner:** quyết định cách xử lý rollback 013–021d:
   phục hồi exact down source nếu có evidence, hoặc lập approved manual recovery
   package; tuyệt đối không bịa rollback cũ. Đóng rõ 016/021 và tên 021c.
4. **Governance owner:** cập nhật `change-register.md`, `kehoach.md §14.2`, đóng hoặc
   chuyển Issue #2; ghi admin merge deviation và evidence S1.
5. **Security owner:** review WF-06 SQL interpolation và DB credential/RLS boundary;
   kiểm thử input injection âm trước khi coi document search an toàn.
6. **Release owner:** xác định thời điểm tạo system `release-manifest.json` thật;
   không dùng synthetic fixture làm production evidence.

## [!] Chưa giải quyết

- Required `TypeScript Build & Lint` không được tạo cho PR ngoài `app/**`.
- Lần TypeScript workflow gần nhất FAILURE do scanner generic `PLACEHOLDER`.
- CI log hiện in dòng bundle khớp; cần scanner quiet/redacted.
- Branch protection yêu cầu approval nhưng single owner không thể self-approve;
  PR #3 đã dùng admin override và `enforce_admins=false`.
- Rollback 021b/021c/021d thiếu; 013–021 chưa theo canonical rollback directory/name.
- Migration 016 có source nhưng không có live record theo evidence; 021c name drift.
- Rollback 022 không thể restore old function tự động do thiếu definition lịch sử.
- Supabase live policies/grants/RLS/function owner chưa được tái xác minh trong S1.
- `change-register.md`, sổ trạng thái `kehoach.md` và Issue #2 chưa phản ánh merge.
- WF-06 dynamic SQL cần kiểm tra injection/authorization boundary.
- System release manifest production chưa tồn tại; prompt registry mới là scaffold.

## Điều kiện GO CYCLE 2

S1 chỉ được đổi từ HOLD sang GO khi có đủ evidence sau:

1. Một `TypeScript Build & Lint` SUCCESS trên current `main` hoặc commit remediation
   kế tiếp, và mọi PR vào `main` luôn tạo required context.
2. Release guard vẫn PASS sau thay đổi CI; scanner không log matched material.
3. Có quyết định change-control được phê duyệt cho rollback 013–021d, tối thiểu
   đóng rõ 021b/021c/021d và thử recovery phù hợp trên môi trường test.
4. Supabase read-only verification PASS cho live migration head, RLS, policies,
   grants, audit append-only và các function security-critical.
5. Governance register/status/Issue được cập nhật đúng evidence, không sửa ngược
   baseline lịch sử.
6. WF-06 injection/authorization review không còn critical finding hoặc có
   remediation package được phê duyệt trước khi tiếp tục phụ thuộc workflow này.

Cho tới khi đủ sáu điều kiện, quyết định chính thức là **HOLD**.
