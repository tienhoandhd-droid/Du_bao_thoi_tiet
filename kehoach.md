# Kế hoạch thực thi CRAVE theo các Chat nhỏ — Codex GPT và Claude Code

> Tệp canonical hiện tại: `kehoach.md` (được đổi tên từ `kehoach.mb` sau lần tạo đầu tiên).
> Ngày lập: 2026-06-28, múi giờ Asia/Ho_Chi_Minh.
> Repo: `tienhoandhd-droid/Du_bao_thoi_tiet`.
> Supabase: `bdttccztjtrcaztjgkot`.
> n8n: `https://n8n.cpc1hn.com`, chỉ phạm vi workflow prefix `TKTL`.
> Roadmap nguồn: `nangcap.md` và ba tệp đính kèm trong đoạn chat lập kế hoạch.
> Trạng thái: kế hoạch thực thi; chưa cho phép tự động thay đổi production.
> **Điểm xuất phát:** hệ thống đã hoàn thành đến Chat 20 (CRAVE Mức 4, eval PASS Hit@5=96,55%) trước khi kế hoạch này được lập; Chat 01–40 ở đây là giai đoạn nâng cấp kiến trúc, không phải khởi động từ đầu. Xem `CLAUDE.md §2` và `nangcap.md §3` để biết trạng thái khởi đầu chi tiết.

## 1. Mô hình phối hợp mới — thay thế mô hình builder/reviewer cũ

Chỉ dẫn mới của người dùng thay thế nguyên tắc cũ “Codex viết, Claude Code kiểm”. Mô hình áp dụng từ kế hoạch này:

1. **Codex GPT và Claude Code đều là người thực hiện độc lập.** Mỗi người được giao các Chat có phạm vi file và đầu ra rõ ràng.
2. **Người nào viết thì người đó tự kiểm ngay trong cùng Chat.** Không bàn giao mặc định cho người còn lại review lại từng dòng.
3. **Một Chat chỉ có một owner.** Owner chịu trách nhiệm inspect, lập plan ngắn, sửa source, chạy test, tự check, báo diff/rủi ro và dừng đúng cổng.
4. **Sau mỗi 5 Chat công việc có một System Check riêng.** System Check không phải code review của người kia; đây là kiểm tra tích hợp toàn hệ thống và source–runtime drift ở chế độ chỉ đọc.
5. **Không hai người sửa cùng file giữa hai System Check.** Nếu cần chạm file đang được Chat khác sở hữu, phải dừng, ghi conflict vào checkpoint và đổi thứ tự Chat.
6. **Các quy tắc an toàn vẫn giữ nguyên:** không tự apply migration/SQL ghi, không update/execute/publish n8n, không đổi GitHub settings/secret, không push/PR khi chưa trình bày kế hoạch thao tác và nhận xác nhận.
7. **Tệp đính kèm và `nangcap.md` ưu tiên hơn dữ kiện cũ trong skill.** Skill `$crave-codex-builder` chỉ được dùng như checklist an toàn và chuẩn chất lượng, không áp lại mô hình Codex→Claude review.
8. **Nhóm <10 người — một người có thể đảm nhận cả hai vai trò trong một Chat.** Ghi rõ trong báo cáo ai làm gì và phân tách DoD; quy tắc an toàn và peer-review vẫn bắt buộc — không gộp "tự viết + tự approve" thành một bước không có evidence. Xem `nangcap.md §19` cho môi trường không có máy local.

## 2. Sáu nguyên tắc quản trị bắt buộc

### Nguyên tắc 1 — Không sửa production trực tiếp; mọi thay đổi đi qua GitHub

Luồng chuẩn bắt buộc, kể cả khi chỉ có một người làm:

```text
Ý tưởng
  → GitHub Issue
  → Branch riêng
  → Code / Migration / Workflow / Prompt
  → Tự kiểm + Test + Eval phù hợp
  → Pull Request
  → Review checklist của chính owner hoặc reviewer được chỉ định
  → Merge vào main
  → Release manifest
  → Kế hoạch triển khai live + xác nhận
  → Release
```

Quy ước tối thiểu:

- Issue ghi objective, phạm vi, risk, acceptance criteria, rollback, owner và Chat liên quan.
- Branch gợi ý: `chat-XX/<ten-ngan>`; hotfix dùng `hotfix/<issue>-<ten-ngan>` và vẫn phải có Issue/PR.
- Commit/PR phải liên kết Issue, liệt kê file, test/eval, migration/workflow/prompt versions và rollback.
- Không dùng Supabase Dashboard, n8n UI hoặc GitHub settings để thực hiện một thay đổi nghiệp vụ mà source chưa có trong branch/PR đã merge.
- Nếu cần thao tác UI để tạo credential hoặc cấu hình platform, Issue/PR phải chứa ADR/runbook/manifest trước; execution ID và evidence được cập nhật sau release.
- Tình huống break-glass chỉ dùng để giảm thiểu sự cố đang diễn ra, phải có incident record, phê duyệt có thẩm quyền và retrospective Issue/PR ngay sau đó; không dùng như đường triển khai bình thường.
- Trong các Chat này, nếu chưa được phép tạo Issue/branch/push/PR remote, owner phải chuẩn bị Issue body, branch name và PR checklist local rồi kết thúc `READY_FOR_GITHUB_APPROVAL`; tuyệt đối không đi thẳng production.

### Nguyên tắc 2 — Mọi migration phải có rollback

Ví dụ convention canonical:

```text
supabase/migrations/013_citation_grounding.sql
supabase/rollbacks/013_citation_grounding_down.sql
```

Quy tắc:

- Forward và rollback dùng cùng số + cùng tên mô tả; rollback thêm hậu tố `_down.sql`.
- Không có rollback thì migration chưa đủ điều kiện mở PR, merge hoặc apply.
- Forward migration phải idempotent ở mức hợp lý; rollback phải hoàn nguyên đúng dependency order và mô tả rõ nguy cơ mất dữ liệu.
- Với migration chứa dữ liệu regulated/append-only, rollback có thể là roll-forward/compatibility restoration thay vì drop dữ liệu; phải ghi rõ lý do và được phê duyệt.
- CI/release validator phải fail khi thiếu rollback, trùng số, sai tên hoặc rollback không được tham chiếu trong manifest.

### Nguyên tắc 3 — Mọi workflow n8n phải export ra GitHub

n8n UI không phải source of truth duy nhất. Mỗi workflow TKTL phải có JSON đã redaction và tài liệu/manifest trong GitHub, ví dụ:

```text
n8n/workflows/TKTL-WF-01-ingest-drive.json
n8n/workflows/TKTL-WF-02-parse-docling.json
n8n/workflows/TKTL-WF-03-embedding.json
n8n/workflows/TKTL-WF-12-ai-agent.json
```

Do live hiện có WF-01–WF-14 với tên/chức năng khác blueprint, filename cuối cùng phải phản ánh **ID live + tên canon trong release manifest**, không renumber workflow chỉ để giống ví dụ. Mỗi export phải lưu:

- workflow ID, name, `versionId`, `activeVersionId`, webhook path và exported-at timestamp;
- node graph, credential **name/placeholder** nhưng không có credential material;
- prompt version, migration dependency, input/output schema, test payload và rollback/unpublish plan;
- secret scan PASS và diff so với bản live/published.

Không workflow nào được publish nếu JSON tương ứng chưa nằm trong branch/PR và release manifest.

### Nguyên tắc 4 — Prompt phải version hóa

Không sửa đè prompt rồi quên lịch sử. Ví dụ:

```text
prompts/answer-with-citation/v1.md
prompts/answer-with-citation/v2.md
prompts/ai-reviewer/v1.md
prompts/google-doc-draft/v1.md
```

Mỗi prompt version phải có `prompt_key`, version, intended use, input/output schema, model constraints, author, reviewer/self-check, effective status, Git SHA và content SHA-256. Quy tắc bắt buộc:

- Prompt approved bất biến; thay đổi bằng version mới, không sửa file version cũ.
- `prompt_version_id`/version phải được ghi trong `ai_queries`, generated document, eval run/result, audit/retrieval/tool log và release manifest khi phù hợp.
- Workflow JSON chỉ tham chiếu prompt version đã có trong GitHub; không để prompt nghiệp vụ chỉ tồn tại trong node n8n.
- Prompt mới/chỉnh sửa quan trọng bắt buộc chạy eval gate trước release.

### Nguyên tắc 5 — Eval là cổng release

Mỗi lần sửa prompt, retrieval, chunking/embedding, workflow RAG/agent hoặc model quan trọng phải chạy golden questions. Cấu trúc ví dụ:

```text
eval/golden-questions/gmp-validation-001.jsonl
eval/reports/2026-06-28-eval-report.md
```

Release gate tối thiểu:

- deterministic retrieval: Hit@5 ≥90%, MRR ≥0,80 và RLS leakage = 0;
- claim-level citation rate ≥95%; no-source refusal = 100%;
- Ragas faithfulness mục tiêu ≥0,90 sau calibration;
- DeepEval custom GMP/citation/no-source/tool controls PASS;
- Promptfoo regression/injection suite PASS;
- report ghi Git SHA, migration, workflow activeVersion, prompt/model/dataset/evaluator versions và threshold.

Nếu citation rate, faithfulness, RLS/no-source hoặc một control critical dưới ngưỡng thì PR/release phải FAIL hoặc HOLD; không được bỏ qua gate bằng cách gọi kết quả “chỉ tham khảo”. Waiver nếu có phải là risk acceptance có owner, expiry và CAPA, không phải chỉnh số thủ công.

### Nguyên tắc 6 — Mỗi Chat phải tích trạng thái rõ ràng

Đầu và cuối mỗi Chat phải cập nhật ba nhóm sau trong change register hoặc sổ trạng thái của tệp này:

- [x] **Đã hoàn thành:** chỉ tích khi có đường dẫn file/evidence, test result và commit/PR hoặc ghi rõ đang ở local vì chưa được phép push.
- [ ] **Kế hoạch:** việc đã được xếp lịch nhưng chưa bắt đầu; ghi owner, dependency và expected output.
- [!] **Chưa giải quyết:** blocker, drift, test fail, quyết định chưa chốt hoặc live action đang chờ xác nhận; ghi impact, owner và next action.

Không dùng từ “đã xong” cho source chưa test, migration chưa có rollback, workflow chưa export, prompt chưa version hoặc thay đổi chưa qua eval gate. Mỗi System Check phải tổng hợp lại cả ba nhóm; item `[!]` critical làm checkpoint `HOLD`.

## 3. Quy tắc bắt buộc cho mọi Chat

- Bắt đầu bằng `git status`, đọc `AGENTS.md`, `nangcap.md`, Chat card hiện tại và các file trực tiếp liên quan.
- Kiểm tra live chỉ đọc khi cần; tuyệt đối không lấy trạng thái cũ làm bằng chứng cho PASS.
- Chỉ làm đúng một Chat; không “tiện tay” sửa hạng mục của Chat sau.
- Mỗi Chat bắt đầu từ Issue/branch hoặc chuẩn bị đầy đủ Issue body/branch name/PR checklist nếu chưa được phép thao tác GitHub remote.
- Migration phải idempotent, có RLS/policy/grant/search path phù hợp và rollback canonical tại `supabase/rollbacks/<NNN>_<ten>_down.sql`.
- Workflow n8n phải export JSON đã redaction vào `n8n/workflows/` trước publish; n8n UI không được là source duy nhất.
- Prompt phải là file version mới trong `prompts/<prompt-key>/vN.md`; output/log/eval ghi prompt version.
- Thay đổi prompt/retrieval/workflow/model quan trọng phải qua golden questions và eval release gate.
- AI retrieval chỉ qua `hybrid_search_v3`; không raw-select nội dung controlled để đưa vào LLM.
- `audit_log`, `retrieval_log`, `tool_call_log` và review evidence chỉ append; không update/delete/truncate lịch sử.
- JWT dùng Cách B: gọi `/auth/v1/user`, có `apikey`, `onError=continueErrorOutput`; không crypto trong n8n Code node.
- Không community node; không secret trong source, frontend, CONFIG node hoặc report.
- Chỉ workflow `TKTL`; không đụng BMS-GMP, VMP, QMSTeam hoặc GMP Kiểm Tạp.
- Mọi AI output GMP là DRAFT; AI không có quyền approve.
- Tự kiểm tối thiểu: syntax/format, unit/static test, negative test phù hợp, secret scan, diff check, file list, rollback và rủi ro còn lại.
- Kết thúc Chat bằng một trong bốn trạng thái: `PASS — sẵn sàng Chat tiếp theo`, `BLOCKED — cần quyết định`, `READY_FOR_GITHUB_APPROVAL — đã chuẩn bị Issue/branch/PR, chờ phép remote`, hoặc `READY_FOR_LIVE_APPROVAL — source đã merge/release package sẵn sàng, chờ phép thao tác live`.
- Trước khi đóng Chat phải cập nhật `[x] Đã hoàn thành`, `[ ] Kế hoạch` và `[!] Chưa giải quyết` có evidence/owner/next action.

Mọi khối **Prompt copy-paste** ở các Chat phía dưới tự động kế thừa sáu nguyên tắc tại mục 2. Khi mở một đoạn chat mới, đặt đoạn bắt buộc sau trước prompt của Chat nếu agent không tự đọc được toàn tệp:

```text
Trước khi làm, đọc kehoach.md mục 2–4 và tuân thủ GitHub-first:
Issue → Branch → Source → Test/Eval → PR → Merge → Release → Live approval.
Không sửa production trực tiếp. Migration phải có rollback cùng số/tên; workflow
phải export JSON vào GitHub; prompt phải version hóa; eval là release gate.
Cuối Chat cập nhật: [x] Đã hoàn thành, [ ] Kế hoạch, [!] Chưa giải quyết.
```

## 4. Cách kiểm tra hệ thống sau mỗi 5 Chat

Mỗi System Check phải tạo một báo cáo tại `docs/checkpoints/system-check-SN.md` và chỉ thực hiện read-only:

1. Ghi Issue, branch, commit/PR/merge/release status, `git status`, file mới/sửa và owner của từng file; không chấp nhận production change không truy ra GitHub flow.
2. Chạy test/lint/build/harness phù hợp cho cả nhóm 5 Chat.
3. Secret scan toàn diff; xác nhận không có key/token/credential export.
4. Đối chiếu từng migration source/rollback cùng số+tên với migration live; thiếu rollback là HOLD, không apply để “thử”.
5. Đối chiếu workflow JSON GitHub với n8n live: ID, name, version, activeVersion, node graph, credential placeholder, webhook; workflow không có export/manifest là HOLD, không update/publish.
6. Đối chiếu prompt file/version/content hash với workflow, output/log/eval và release manifest; prompt sửa đè hoặc thiếu version là HOLD.
7. Xác nhận mọi thay đổi prompt/retrieval/workflow/model thuộc nhóm đã chạy golden questions và eval gate; report/threshold/versions có thể tái lập.
8. Đối chiếu frontend/CI/release manifest với GitHub state; không push hoặc đổi settings khi chưa có xác nhận.
9. Kiểm RLS, grants, append-only, JWT Cách B, `hybrid_search_v3`, approved-only, citation/no-source và human-review boundaries.
10. Tổng hợp `[x] Đã hoàn thành`, `[ ] Kế hoạch`, `[!] Chưa giải quyết`; liệt kê drift mới, regression, file conflict, dữ kiện chưa xác minh và quyết định go/hold.
11. System Check PASS không tự động cho phép thao tác production; mỗi thao tác live vẫn cần kế hoạch và xác nhận riêng.

## 5. Bảng phân công tổng thể

| Chu kỳ | Chat công việc | Chủ đề | Codex GPT | Claude Code | Checkpoint |
|---|---:|---|---:|---:|---|
| 1 | 01–05 | Baseline, GitHub, Supabase/n8n source, repo control plane | 01, 03, 05 | 02, 04 | S1 — Claude Code |
| 2 | 06–10 | Security và Docling/document versioning | 06, 09, 10 | 07, 08 | S2 — Codex GPT |
| 3 | 11–15 | Embedding, observability và schema nghiệp vụ | 11, 14 | 12, 13, 15 | S3 — Claude Code |
| 4 | 16–20 | Hybrid RAG, citation, RLS và audit instrumentation | 16, 18, 20 | 17, 19 | S4 — Codex GPT |
| 5 | 21–25 | Eval bốn lane và controlled DRAFT | 22, 24 | 21, 23, 25 | S5 — Claude Code |
| 6 | 26–30 | Google Docs, frontend, backup và validation | 27, 29 | 26, 28, 30 | S6 — Codex GPT |
| 7 | 31–35 | P1 glossary UI, reviewer, agent, dashboard, supply chain | 31, 33, 35 | 32, 34 | S7 — Claude Code |
| 8 | 36–40 | P2 knowledge graph, cache, scaling, observability, local LLM | 37, 39 | 36, 38, 40 | S8 — Codex GPT |

Tổng công việc: **Codex GPT 20 Chat, Claude Code 20 Chat**. Tám System Check được chia đều bốn checkpoint mỗi người.

## 6. Chu kỳ 1 — Baseline và control plane

### Chat 00 — Transition Handoff (đã hoàn thành trước kế hoạch này)

- **Ý nghĩa:** Toàn bộ lịch sử CRAVE từ Chat 01–20 (theo đánh số cũ trong `CLAUDE.md`) đã xong trước khi kế hoạch này được lập. Trạng thái khởi đầu: Mức 4, FTS eval PASS 96,55%, 14 workflow active, migration 001–022 applied trên `bdttccztjtrcaztjgkot`.
- **Không cần thực thi thêm.** Chat 00 chỉ là mốc tham chiếu; nếu cần bằng chứng, xem `CLAUDE.md §2 Nhật ký theo Chat` và `nangcap.md §3 Kiểm tra trạng thái`.
- **Ảnh hưởng đến Chat 01+:** snapshot đầu kỳ (Chat 01 mới) bắt đầu từ migration 022 đã live, 33 bảng/14 workflow/58 câu golden active; không phải từ `013`.

---

### Chat 01 — Codex GPT — Snapshot, change register và file ownership

- **Mục tiêu:** đóng băng bằng chứng đầu kỳ và tạo sổ điều phối để hai người không sửa đè nhau.
- **Đầu vào:** `AGENTS.md`, `nangcap.md`, repo tree, trạng thái Git/Supabase/n8n/GitHub chỉ đọc.
- **Phạm vi file:** `docs/governance/change-register.md`, `docs/governance/file-ownership.md`, `docs/architecture/current-state-snapshot.md`.
- **Việc làm:** ghi Issue/branch/commit/PR/release status cùng 33 bảng/14 workflow, migration live tới 022, credential inventory theo tên, GitHub settings, known drift; lập bảng file lease cho Chat 01–05.
- **Tự kiểm:** không ghi secret value; mọi con số có thời điểm/source; secret scan; link nội bộ hợp lệ.
- **DoD:** ba tài liệu đủ để tái lập baseline và biết ai sở hữu file nào.
- **Rollback:** xóa/revert ba tài liệu local; không có rollback live.
- **Điểm dừng:** không đổi settings, không export dữ liệu GMP thật.

**Prompt copy-paste**

```text
Bạn là Codex GPT, owner Chat 01 của CRAVE. Đọc AGENTS.md, nangcap.md và kiểm tra
repo + GitHub + Supabase + n8n ở chế độ chỉ đọc. Tạo current-state snapshot,
change register và file ownership cho Chat 01–05. Không sửa production, không
push, không ghi secret value. Tự kiểm timestamp/source, secret scan và diff.
Kết thúc bằng file list, dữ kiện chưa chắc, rollback và PASS/BLOCKED.
```

### Chat 02 — Claude Code — GitHub secret/branch hardening source package

- **Mục tiêu:** chuẩn bị source và runbook để đưa service-role key ra khỏi Variables và bảo vệ `main`.
- **Phạm vi file:** `.github/workflows/eval.yml`, `.github/workflows/ci.yml`, `docs/sop/github-secret-rotation.md`, `docs/governance/github-branch-policy.md`.
- **Việc làm:** dùng `secrets.SUPABASE_SERVICE_ROLE_KEY`, least permissions, concurrency, safe triggers, required-check proposal, rotate/revoke order; không đổi GitHub settings thật.
- **Tự kiểm:** workflow syntax; fork/untrusted input analysis; log không echo secret; action permissions tối thiểu.
- **DoD:** diff local và runbook có dry-run/rollback; liệt kê thao tác remote cần xác nhận.
- **Rollback:** revert file workflow; khóa cũ không bao giờ quay lại Variable.

**Prompt copy-paste**

```text
Bạn là Claude Code, owner Chat 02. Tự inspect và tự review GitHub Actions của
CRAVE. Chỉ tạo source/runbook local để chuyển service-role từ vars sang secrets,
least permissions và bảo vệ main. Không đổi GitHub settings, không rotate key,
không push. Validate YAML, phân tích untrusted events/log leakage, secret scan và
diff check. Báo thao tác remote cần người dùng duyệt; kết thúc PASS/BLOCKED.
```

### Chat 03 — Codex GPT — Reconcile Supabase source tới migration 022

- **Mục tiêu:** Git có bằng chứng tái tạo đúng trạng thái live trước migration mới.
- **Phạm vi file:** `supabase/baseline/`, `supabase/migrations/022_fix_eval_rank_order.sql`, `supabase/rollbacks/022_fix_eval_rank_order_down.sql`, `docs/architecture/supabase-source-map.md`.
- **Việc làm:** đọc live definition, phục hồi exact semantics đã redaction, lập bản đồ 001–022 và gaps 001–012/021b–d.
- **Tự kiểm:** compare function/table/policy/grant; SQL parse/static check; không apply; không bịa rollback nếu live không đủ bằng chứng.
- **DoD:** source map phân loại `exact`, `baseline-only`, `missing evidence`; 022 source khớp live.
- **Rollback:** revert source artifacts; production không đổi.

**Prompt copy-paste**

```text
Bạn là Codex GPT, owner Chat 03. Inspect Supabase project bdttccztjtrcaztjgkot
read-only và repo migrations. Reconcile source tới migration 022, tạo source map
001–022 và phục hồi 022 chỉ khi definition live đủ bằng chứng. Không execute SQL
ghi/apply. Tự check SQL, functions/policies/grants, idempotency, rollback honesty,
secret scan và diff. Kết thúc PASS/BLOCKED với các gap cần xử lý.
```

### Chat 04 — Claude Code — Export và reconcile đủ 14 workflow TKTL

- **Mục tiêu:** repo có 14/14 workflow source đã redaction và manifest version chính xác.
- **Phạm vi file:** `n8n/workflows/`, `n8n/workflow-docs/`, `n8n/release-manifest.json`.
- **Việc làm:** inspect/export read-only WF-01…WF-14; lưu ID/name/version/activeVersion/webhook/node graph/credential name; loại secret/literal Tavily value.
- **Tự kiểm:** parse toàn JSON; compare live graph; JWT Cách B; chỉ TKTL; phát hiện WF-14 draft/published drift.
- **DoD:** 14 JSON canon hoặc ghi rõ workflow nào bị MCP redaction nên chưa thể canon; không có credential material.
- **Rollback:** revert artifacts; không import/update/publish.

**Prompt copy-paste**

```text
Bạn là Claude Code, owner Chat 04. Reconcile read-only 14 workflow TKTL với repo.
Tạo workflow source/docs/manifest đã redaction; không đụng workflow dự án khác,
không update/execute/publish n8n. Tự parse JSON, compare ID/version/node/webhook,
kiểm JWT Cách B, credential placeholder và secret scan, đặc biệt WF-14/Tavily.
Kết thúc PASS/BLOCKED và nêu field không thể xác minh.
```

### Chat 05 — Codex GPT — Repo target structure, release manifest và CI guardrails

- **Mục tiêu:** tạo khung repo đích mà không big-bang move frontend hoặc trộn production change.
- **Phạm vi file:** thư mục `docs/`, `prompts/`, `eval/`, `scripts/`; `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`; script validate release manifest; không move `app/`.
- **Việc làm:** tạo Issue/PR template và placeholder/readme có owner/purpose; kiểm manifest Git SHA/migration+rollback/WF export/prompt/model/dataset; guard secret/missing rollback/missing workflow/unversioned prompt.
- **Tự kiểm:** CI chạy trên dữ liệu giả; không tạo source trùng; không commit report GMP thật.
- **DoD:** cây repo và validator sẵn sàng cho các Chat sau; P0 không đổi build path.
- **Rollback:** revert scaffold/validator.

**Prompt copy-paste**

```text
Bạn là Codex GPT, owner Chat 05. Tạo scaffold repo đích và release-manifest
validator theo nangcap.md, không move app/, không sửa live, không push. Guard phải
phát hiện migration/workflow/rollback thiếu và secret pattern nhưng không log
secret. Tự chạy validator positive/negative, secret scan và diff check. Báo file
ownership cho chu kỳ sau và kết thúc PASS/BLOCKED.
```

### System Check S1 — Claude Code — Sau Chat 01–05

- **Phạm vi:** baseline, GitHub source package, Supabase/n8n reconciliation và repo scaffold.
- **Bắt buộc kiểm:** 022/14 workflow/manifest khớp snapshot; không secret; không file conflict; CI/source-only tests; live vẫn không đổi.
- **Đầu ra:** `docs/checkpoints/system-check-S1.md` với quyết định `GO CYCLE 2` hoặc `HOLD`.

```text
Bạn là Claude Code, owner System Check S1. Không review theo mô hình cũ và không
sửa code tính năng. Kiểm tích hợp read-only toàn bộ đầu ra Chat 01–05 theo mục 4
của kehoach.md; chạy test/secret scan/manifest checks và đối chiếu live. Tạo
system-check-S1.md, ghi drift/conflict/risk và GO CYCLE 2 hoặc HOLD. Không apply,
update/publish, đổi GitHub settings hay push.
```

## 7. Chu kỳ 2 — Security và Docling/document versioning

### Chat 06 — Codex GPT — Migration 023 security/eval hardening

- **Mục tiêu:** đóng RPC eval đặc quyền và policy quá rộng mà không làm gãy RLS.
- **Phạm vi file:** `supabase/migrations/023_security_eval_hardening.sql`, `supabase/rollbacks/023_security_eval_hardening_down.sql`, SQL tests.
- **Việc làm:** lock `search_path`, revoke PUBLIC/anon/authenticated phù hợp, cap input/workload, policy role/owner; không revoke mù `user_has_role/any_role`.
- **Tự kiểm:** idempotency; anon/user negative; backend positive; advisor delta dự kiến; rollback dependency.
- **DoD:** source/tests PASS, sẵn sàng trình người dùng xem SQL; chưa apply.
- **Rollback:** 023_down được review; ưu tiên roll-forward nếu đã có production use.

```text
Bạn là Codex GPT, owner Chat 06. Tạo migration 023 + rollback + tests từ schema
live read-only. Harden run_fts_eval_v1/grants/search_path/eval policies, không
đụng user_has_role mù. Không apply/execute SQL ghi. Tự check idempotency, RLS
positive/negative, function signature, rollback và secret scan. Kết thúc READY
FOR LIVE APPROVAL hoặc BLOCKED, kèm full file list và risk.
```

### Chat 07 — Claude Code — Docling local spike 5 file

- **Mục tiêu:** chứng minh parser/manifest/chunk strategy trên 5 file đại diện mà không nối production.
- **Phạm vi file:** `scripts/ingest/docling_spike/`, `docs/validation/docling-spike-protocol.md`, dữ liệu giả/fixture không nhạy cảm.
- **Việc làm:** PDF, DOCX, PPTX, XLSX và image/email representative; output Markdown/JSON; page/table/heading; parser version; SHA-256; error classification.
- **Tự kiểm:** repeatability, same-file same-hash, resource use, OCR/table manual sample; không gửi tài liệu ra ngoài.
- **DoD:** 5/5 có manifest hoặc lỗi giải thích được; quyết định chunk schema có bằng chứng.
- **Rollback:** xóa local artifacts/cache; không có DB mutation.

```text
Bạn là Claude Code, owner Chat 07. Làm Docling local spike với 5 fixture không
nhạy cảm. Tạo script/protocol/manifest Markdown+JSON có parser version, SHA-256,
page/table/heading và lỗi. Không nối Supabase/n8n/Drive, không tải dữ liệu GMP.
Tự test repeatability/hash/OCR-table sample/resource use, secret scan và diff.
Kết thúc PASS/BLOCKED cùng recommendation cho Chat 08–10.
```

### Chat 08 — Claude Code — Docling worker và acceptance set 20 file

- **Mục tiêu:** biến spike thành worker local có retry/idempotency/queue và nghiệm thu 20 file.
- **Phạm vi file:** `scripts/ingest/docling_worker/`, manifest schema, test fixtures, `docs/validation/docling-oq.md`.
- **Việc làm:** hỗ trợ PDF/DOCX/PPTX/XLSX/image/email; raw/parsed artifact paths; timeout/retry/quarantine; source ID+hash dedupe.
- **Tự kiểm:** ≥95% parse success; reingest không duplicate; corrupted/password file fail-safe; path traversal/zip bomb controls.
- **DoD:** 20-file report, parser pin, reproducible install, no external data egress.
- **Rollback:** stop worker; quarantine local output; remove generated fixtures.

```text
Bạn là Claude Code, owner Chat 08. Nâng Docling spike thành local worker và bộ OQ
20 file. Không kết nối production. Tự test retry/idempotency/corrupt/password/
path traversal/resource limits; yêu cầu ≥95% success và manifest truy nguyên.
Pin dependencies, secret scan, diff check và ghi rollback. Kết thúc PASS/BLOCKED.
```

### Chat 09 — Codex GPT — Migration 024 document versions và backfill dry-run

- **Mục tiêu:** tạo logical document + immutable version + chunk provenance.
- **Phạm vi file:** `supabase/migrations/024_document_versions.sql`, `supabase/rollbacks/024_document_versions_down.sql`, backfill/report tests.
- **Việc làm:** `document_versions`, version/hash/parser/raw/parsed metadata, chunk FK/content hash; compatibility với 12 documents/65 chunks hiện có; thêm `version_status`/`newer_version_url`/`last_verified_at` cho bảng `documents` và RPC `update_document_version_status()` (SECURITY DEFINER, audit).
- **Tự kiểm:** backfill dry-run 12/65; unique/FK/RLS; approved version immutable; rollback/data-retention; no generated column conflict; kiểm RPC chỉ QA/Admin đổi được `version_status`, AI không ghi.
- **DoD:** migration source và dry-run PASS; không null version sau backfill simulation.

```text
Bạn là Codex GPT, owner Chat 09. Tạo migration 024 + rollback + dry-run tests cho
document_versions và chunk provenance từ live schema read-only. Không apply.
Tự check 12 documents/65 chunks mapping, RLS/FK/unique/immutability, idempotency,
rollback/data retention và secret scan. Kết thúc READY FOR LIVE APPROVAL hoặc
BLOCKED; không bịa cột live chưa xác minh.
```

### Chat 10 — Codex GPT — WF-10/WF-15/WF-01 ingestion contract

- **Mục tiêu:** thiết kế source-only luồng Drive → Docling local → ingest coordinator, không chạy/import.
- **Phạm vi file:** `n8n/workflows/TKTL-WF-10-google-drive-sync.json`, `n8n/workflows/TKTL-WF-15-docling-parse-orchestrator.json`, `n8n/workflows/TKTL-WF-01-document-ingest.json`, workflow docs và test payload/manifest.
- **Việc làm:** source file events, allowlist folder, idempotency, parse callback, version/hash, approved-only gate, error/quarantine/audit.
- **Tự kiểm:** JSON parse; only TKTL; JWT Cách B nếu có webhook; no crypto/community/secret; credential placeholder; replay/out-of-order tests.
- **DoD:** ba workflow contract rõ; không tự approve; local mock PASS.
- **Rollback:** discard drafts; live workflow không đổi.

```text
Bạn là Codex GPT, owner Chat 10. Tạo source-only workflow contract/draft cho
WF-10 Drive transport, WF-15 Docling orchestrator và WF-01 ingest coordinator.
Không import/update/execute/publish. Dùng manifest từ Chat 08, idempotency/hash/
version/quarantine/approved-only. Tự parse JSON, test replay/out-of-order/JWT,
secret scan và chỉ TKTL. Kết thúc PASS/BLOCKED.
```

### System Check S2 — Codex GPT — Sau Chat 06–10

- **Phạm vi:** migration 023/024, Docling 5→20 file và ingestion workflow contracts.
- **Bắt buộc kiểm:** SQL source vs live; Docling acceptance; manifest compatibility với workflow/schema; không production mutation.
- **Đầu ra:** `docs/checkpoints/system-check-S2.md` và `GO CYCLE 3`/`HOLD`.

```text
Bạn là Codex GPT, owner System Check S2. Kiểm tích hợp read-only Chat 06–10:
migration 023/024, Docling OQ 20 file và manifest→WF contracts. Chạy tests, secret
scan, schema/JSON compatibility và đối chiếu live không đổi. Không apply/import/
execute/publish/push. Tạo system-check-S2.md, nêu drift/conflict và GO/HOLD.
```

## 8. Chu kỳ 3 — Embedding, observability và schema nghiệp vụ

### Chat 11 — Codex GPT — Chunking và embedding pipeline

- **Mục tiêu:** biến parsed artifact thành chunk có provenance và embedding đầy đủ.
- **Phạm vi file:** `scripts/ingest/chunk_embed/`, WF-01 subflow draft, prompt/config docs, test payloads.
- **Việc làm:** chunk heading/page/table; deterministic `content_hash`; token limit/overlap; batch embedding `text-embedding-3-small` 1536; retry/rate limit; approved-only before retrieval.
- **Tự kiểm:** 100% controlled chunk có version/hash/embedding trong fixture; same content không embed lại; dimension/model mismatch fail-safe; no raw secret.
- **DoD:** local/mock pipeline PASS và metrics report; không gọi production nếu chưa xác nhận.
- **Rollback:** disable subflow/feature flag; preserve parsed artifacts and logs.

```text
Bạn là Codex GPT, owner Chat 11. Xây chunk+embed pipeline source local từ manifest
Docling/024 schema. Không ghi production hoặc chạy n8n live. Chunk theo heading/
page/table, content hash, idempotent embedding 1536, retry/rate limit và approved-
only. Tự test hash/dedupe/dimension/failure/100% fixture coverage, secret scan và
diff. Kết thúc PASS/BLOCKED hoặc READY FOR LIVE APPROVAL.
```

### Chat 12 — Claude Code — Migration 025 AI observability

- **Mục tiêu:** tạo `retrieval_log`, `tool_call_log` và trace/release fields append-only.
- **Phạm vi file:** `supabase/migrations/025_ai_observability.sql`, `supabase/rollbacks/025_ai_observability_down.sql`, SQL tests.
- **Việc làm:** trace FK/index/RLS; insert-only policies/functions; redacted details; workflow/prompt/model/release identifiers; block mutation history.
- **Tự kiểm:** anon/user/service-role matrix; update/delete/truncate denied; function search path/grants; log không chứa token/raw secret.
- **DoD:** migration/tests idempotent PASS; event storage đủ cho Chat 20/22–25.
- **Rollback:** có dependency guard; không drop history khi đã có regulated data mà không change control.

```text
Bạn là Claude Code, owner Chat 12. Tạo migration 025 + rollback + SQL tests cho
retrieval_log/tool_call_log/trace fields từ schema live read-only. Không apply.
Tự review RLS/grants/search_path/append-only, mutation negative tests, idempotency,
redaction và rollback dependency. Kết thúc READY FOR LIVE APPROVAL hoặc BLOCKED.
```

### Chat 13 — Claude Code — Audit event matrix và logging contract

- **Mục tiêu:** định nghĩa một contract duy nhất để query/retrieval/tool/draft/review/export có trace đầy đủ.
- **Phạm vi file:** `docs/architecture/audit-event-matrix.md`, `docs/architecture/trace-contract.md`, shared test schemas/fixtures.
- **Việc làm:** event name, actor, entity, trace, input/output hash, source/release IDs, redaction, retention, failure events; mapping bảng và workflow.
- **Tự kiểm:** every critical event exactly once; no secret/raw sensitive defaults; ALCOA+ review; correlation across retries.
- **DoD:** event matrix 100% P0 paths; owners and required/optional fields explicit.
- **Rollback:** docs revert; không thay audit live.

```text
Bạn là Claude Code, owner Chat 13. Thiết kế audit event matrix và trace contract
cho toàn P0 theo nangcap.md/025 source. Không sửa live. Tự kiểm ALCOA+, retry/
duplicate semantics, redaction, retention, event completeness và no-secret.
Tạo fixtures/schema validation nếu cần; kết thúc PASS/BLOCKED với mapping tới
từng workflow/table và file owner cho Chat 20.
```

### Chat 14 — Codex GPT — Migration 026 generated documents và reviews

- **Mục tiêu:** generalize `generated_protocols`/`protocol_reviews` thành controlled DRAFT model mà không mất dữ liệu cũ.
- **Phạm vi file:** `supabase/migrations/026_generated_docs_reviews.sql`, `supabase/rollbacks/026_generated_docs_reviews_down.sql`, compatibility/backfill tests.
- **Việc làm:** `generated_docs`, `doc_reviews`, template/prompt/source IDs, state `DRAFT/REVIEW/APPROVED/REJECTED/SUPERSEDED`, snapshot hash; segregation of duties.
- **Tự kiểm:** old-data mapping; creator≠reviewer; service/AI cannot approve; append-only review; state transition matrix.
- **DoD:** dry-run migration and compatibility PASS; no duplicate source of truth.
- **Rollback:** compatibility view/roll-forward plan; never silently drop reviews/snapshots.

```text
Bạn là Codex GPT, owner Chat 14. Tạo migration 026 + rollback + tests để
generalize generated_protocols/protocol_reviews thành generated_docs/doc_reviews.
Không apply. Tự check backfill/compatibility, state machine, segregation of duties,
AI no-approve, RLS, idempotency, snapshot hash và rollback/data retention.
Kết thúc READY FOR LIVE APPROVAL hoặc BLOCKED.
```

### Chat 15 — Claude Code — Migration 027 glossary và equipment normalization

- **Mục tiêu:** chuẩn hóa glossary EN–VI P0 và equipment registry; relationship chỉ được mở khi P2.
- **Phạm vi file:** `supabase/migrations/027_glossary_equipment.sql`, `supabase/rollbacks/027_glossary_equipment_down.sql`, seed giả/tests.
- **Việc làm:** migrate/compatibility `glossary`→`glossary_terms`; term version/source/approval; normalize equipment fields; feature-gate relationship schema.
- **Tự kiểm:** approved/effective term only; version immutability; unique equipment code; AI cannot approve qualification/relationship; RLS matrix.
- **DoD:** không có hai bảng cùng nghĩa; 100 term fixture import/test; rollback rõ.

```text
Bạn là Claude Code, owner Chat 15. Tạo migration 027 + rollback + tests cho
glossary_terms và equipment normalization, đọc live schema trước. Không apply.
Không tạo hai source of truth; relationships phải gated cho P2. Tự check RLS,
version/source/approval, equipment uniqueness, compatibility, idempotency và
rollback. Kết thúc READY FOR LIVE APPROVAL hoặc BLOCKED.
```

### System Check S3 — Claude Code — Sau Chat 11–15

- **Phạm vi:** chunk/embed, migrations 025–027, audit/trace contract.
- **Bắt buộc kiểm:** schema compatibility 023–027; không circular FK/rollback; event/trace fields khớp workflow pipeline; P0 glossary approved-only.
- **Đầu ra:** `docs/checkpoints/system-check-S3.md` và `GO CYCLE 4`/`HOLD`.

```text
Bạn là Claude Code, owner System Check S3. Kiểm tích hợp read-only Chat 11–15,
đặc biệt migration order 023–027, rollback/FK/RLS, chunk embedding contract,
trace/event matrix và glossary approval. Chạy static/fixture tests, secret scan,
đối chiếu live không đổi. Tạo system-check-S3.md và GO/HOLD; không apply/push.
```

## 9. Chu kỳ 4 — Hybrid RAG, citation, RLS và audit instrumentation

### Chat 16 — Codex GPT — `hybrid_search_v3` hardening và retrieval contract

- **Mục tiêu:** có một cổng retrieval vector+FTS+metadata/RLS có score rõ và không bypass quyền.
- **Phạm vi file:** migration/function source bổ sung theo version mới được System Check chốt, retrieval tests/benchmarks.
- **Việc làm:** vector candidate + FTS/BM25-like rank + metadata; merge/rerank inputs; approved/effective/version filters; identity từ auth context; thresholds/top-k caps.
- **Tự kiểm:** explain/query plan; Hit@k fixture; user A/B negative; anon fail; superseded/unapproved excluded; SQL injection inputs.
- **DoD:** single retrieval contract có version và deterministic fallback; không raw content endpoint cho AI.
- **Rollback:** feature flag/previous function version; fail closed nếu grounding gate hỏng.

```text
Bạn là Codex GPT, owner Chat 16. Harden source hybrid_search_v3 theo schema 024/
025/027 và live signature. Chỉ tạo source/tests, không apply SQL. Identity phải từ
auth context; approved/effective/version/RLS; vector+FTS+metadata và caps. Tự test
user A/B, anon, superseded, injection, Hit@k và query plan. Kết thúc READY FOR
LIVE APPROVAL hoặc BLOCKED với rollback/fallback.
```

### Chat 17 — Claude Code — Query normalization, glossary VI→EN và rerank

- **Mục tiêu:** câu hỏi tiếng Việt tìm đúng tài liệu tiếng Anh mà không trôi ý hoặc dùng term chưa duyệt.
- **Phạm vi file:** immutable next version `prompts/answer-with-citation/vN.md` hoặc sub-prompt version có manifest, query-expansion module/workflow stage, bilingual test set.
- **Việc làm:** normalize, acronym/alias, approved glossary, preserve numbers/equipment codes, multi-query cap, rerank contract; record expanded query hash và `prompt_version`.
- **Tự kiểm:** VI→EN pairs, typo, acronym, conflicting terms, unapproved glossary exclusion, prompt injection and cost/latency cap.
- **DoD:** bilingual test PASS theo threshold; output expansion auditable and reversible.
- **Rollback:** disable expansion; FTS/vector original-query degraded mode có audit label.

```text
Bạn là Claude Code, owner Chat 17. Xây query normalization/glossary VI→EN/rerank
stage source local, dùng approved glossary và hybrid_search_v3 contract. Không
update/run workflow live. Tự test số/mã thiết bị/acronym/typo/conflict/unapproved
term/injection/latency, secret scan và diff. Ghi degraded-mode rollback; kết thúc
PASS/BLOCKED.
```

### Chat 18 — Codex GPT — Claim-level citation answer workflow

- **Mục tiêu:** mọi claim nghiệp vụ có `chunk_id`/document version/page và từ chối khi thiếu nguồn.
- **Phạm vi file:** `n8n/workflows/TKTL-WF-02-rag-query.json`, immutable `prompts/answer-with-citation/vN.md`, answer schema và citation mapping tests.
- **Việc làm:** consume retrieval contract; structured claims/sources; answer Vietnamese; save `ai_queries`/`ai_query_sources` cùng `prompt_version`; no-source/unsupported states; disclaimer.
- **Tự kiểm:** citation coverage; stale/superseded source; conflicting documents; invalid model JSON; source user không có quyền; no-source 100%.
- **DoD:** claim citation mục tiêu ≥95%, no-source 100%, no raw secret; chưa publish/run live.
- **Rollback:** route về search-only/no-answer fail-closed.

```text
Bạn là Codex GPT, owner Chat 18. Nâng source/draft WF-02 và prompt để trả lời có
claim-level citation, lưu query/source trace và từ chối thiếu nguồn. Không update/
execute/publish n8n. Tự parse JSON, test citation≥95%, no-source 100%, conflicting/
superseded/unauthorized source, invalid model output, JWT Cách B và secret scan.
Kết thúc PASS/BLOCKED.
```

### Chat 19 — Claude Code — RLS, JWT và injection negative-test suite

- **Mục tiêu:** chứng minh không rò tài liệu hoặc quyền qua database, workflow hay prompt.
- **Phạm vi file:** `eval/security/`, `n8n/test-payloads/security/`, RLS fixture/runbook.
- **Việc làm:** two-user/two-role/department; anon/expired/forged JWT; body user_id spoof; SQL/prompt/tool injection; CORS; unapproved/superseded source.
- **Tự kiểm:** test độc lập và deterministic; expected deny rõ; không dùng production records; không log token.
- **DoD:** 0 RLS leakage; all deny cases PASS; false-negative test chứng minh suite có thể fail.
- **Rollback:** test-only artifacts; không nới policy để test xanh.

```text
Bạn là Claude Code, owner Chat 19. Tạo security negative-test suite cho RLS/JWT
Cách B/injection/CORS bằng fixtures giả. Không ghi production hoặc chạy workflow
live. Tự chứng minh suite bắt được một failure injection; 0 leakage, no token log,
body user_id không được tin. Secret scan và diff; kết thúc PASS/BLOCKED.
```

### Chat 20 — Codex GPT — Instrument audit/retrieval/tool logs vào workflows

- **Mục tiêu:** mọi đường query/retrieval/tool/draft/review/export có trace đúng event matrix.
- **Phạm vi file:** shared n8n subflow/source và mọi `n8n/workflows/TKTL-WF-*.json` bị ảnh hưởng; integration fixtures; release manifest entries.
- **Việc làm:** trace propagation, input/output hash server-side, insert-only logs, retry semantics, redaction, error events; max agent iteration metadata.
- **Tự kiểm:** exactly-once logical event under retry; no update/delete; no secret; JSON parse; JWT/user identity; only TKTL.
- **DoD:** event matrix coverage 100% trên mock integration; live chưa đổi.
- **Rollback:** disable instrumentation feature flag while preserving existing history.

```text
Bạn là Codex GPT, owner Chat 20. Instrument source-only workflow/subflow theo
audit-event-matrix và migration 025. Không import/update/run/publish. Chỉ INSERT,
trace/retry/redaction/hash, không crypto node hoặc secret. Tự test duplicate retry,
error path, event coverage 100%, JSON/JWT và secret scan. Kết thúc PASS/BLOCKED.
```

### System Check S4 — Codex GPT — Sau Chat 16–20

- **Phạm vi:** hybrid retrieval, bilingual expansion, citation answer, security suite và log instrumentation.
- **Bắt buộc kiểm:** end-to-end fixture từ query→source→claim→logs; 0 RLS leak; no-source; score/identity/citation trace nhất quán.
- **Đầu ra:** `docs/checkpoints/system-check-S4.md` và `GO CYCLE 5`/`HOLD`.

```text
Bạn là Codex GPT, owner System Check S4. Chạy integration read-only/fixture cho
Chat 16–20 từ bilingual query đến claim citation và logs. Kiểm 0 RLS leakage,
no-source, approved-only, JWT, secret scan, source/runtime drift; không apply/run
live/push. Tạo system-check-S4.md và GO/HOLD với regression/risk cụ thể.
```

## 10. Chu kỳ 5 — Eval bốn lane và controlled DRAFT

### Chat 21 — Claude Code — Deterministic retrieval eval và metric repair

- **Mục tiêu:** có baseline không phụ thuộc LLM judge và sửa việc dùng sai cột faithfulness/relevancy cho RR/hit.
- **Phạm vi file:** `eval/retrieval/`, migration/source metric repair nếu cần, golden dataset version/loader, CI job draft.
- **Việc làm:** Hit@1/5, rank, MRR, latency, RLS/no-source; 50–100 golden questions có owner/category/source expectation; release metadata.
- **Tự kiểm:** deterministic repeat; dataset leakage; old-run compatibility; intentional regression makes gate fail; no service key in Variables/source.
- **DoD:** Hit@5 target ≥90%, MRR ≥0,80; metric semantics đúng; CI source-only/local PASS.
- **Rollback:** preserve eval history; disable new job without relabeling old values.

```text
Bạn là Claude Code, owner Chat 21. Xây deterministic retrieval eval và sửa metric
semantics source-only, dùng golden 50–100 câu versioned. Không chạy RPC live/ghi
production. Tự test repeatability, Hit@k/MRR/RLS/no-source, intentional failure,
old-run compatibility, CI permissions và secret scan. Kết thúc PASS/BLOCKED.
```

### Chat 22 — Codex GPT — Ragas RAG quality lane

- **Mục tiêu:** đo faithfulness, answer relevancy, context precision/recall đúng nghĩa.
- **Phạm vi file:** `eval/ragas/`, dataset adapter, evaluator config, report schema, CI job draft.
- **Việc làm:** map query/context/answer/ground truth; judge model/version; seeded/calibrated sample; cost cap; trace to eval run/result.
- **Tự kiểm:** calibration với QA-labelled subset; repeated-run variance; timeout/error; no raw secret/report data committed.
- **DoD:** faithfulness target ≥0,90 sau calibration; report phân biệt Ragas và retrieval metrics.
- **Rollback:** disable judge job, giữ deterministic gate và history.

```text
Bạn là Codex GPT, owner Chat 22. Tạo Ragas lane local/CI source cho RAG quality,
không chạy production hoặc commit dữ liệu GMP. Map dataset/output đúng metric,
pin evaluator version, cost cap và trace. Tự test calibration, repeat variance,
timeout/error, secret/data leak và schema semantics. Kết thúc PASS/BLOCKED.
```

### Chat 23 — Claude Code — DeepEval custom GMP/citation/no-source/tool lane

- **Mục tiêu:** tạo test dạng pytest cho control đặc thù mà Ragas không bao phủ tốt.
- **Phạm vi file:** `eval/deepeval/`, custom metrics/assertions, fixtures, CI job draft.
- **Việc làm:** citation completeness, no-source refusal, approved-only, tool allowlist/iteration, DRAFT/no-approve, prompt injection assertions.
- **Tự kiểm:** positive/negative fixtures; intentional violations fail; judge/custom deterministic split; dependency lock.
- **DoD:** suite chạy độc lập; mọi critical control có test ID và traceability.
- **Rollback:** disable lane, không xóa evidence/run history.

```text
Bạn là Claude Code, owner Chat 23. Tạo DeepEval/pytest lane cho GMP citation,
no-source, approved-only, tool allowlist và AI no-approve bằng dữ liệu giả. Không
chạy live. Tự test positive/negative và intentional violations, lock dependency,
judge variability, secret scan và trace IDs. Kết thúc PASS/BLOCKED.
```

### Chat 24 — Codex GPT — Promptfoo red-team và consolidated release gate

- **Mục tiêu:** chặn prompt regression/injection và hợp nhất bốn lane thành quyết định release có thể truy nguyên.
- **Phạm vi file:** `eval/promptfoo/`, `.github/workflows/eval.yml`, release-gate script/config, report summary.
- **Việc làm:** prompt/model matrix, injection/exfiltration/no-source cases; consume deterministic/Ragas/DeepEval outputs; threshold/version/release manifest.
- **Tự kiểm:** one-lane failure blocks release; fork PR không nhận secret; job permissions/timeout/cache; report không trộn metric.
- **DoD:** four-lane gate deterministic; output `PASS/FAIL/BLOCKED` với reason codes.
- **Rollback:** disable costly lanes only bằng change control; deterministic/security gate vẫn giữ.

```text
Bạn là Codex GPT, owner Chat 24. Tạo Promptfoo red-team và consolidated release
gate cho 4 lane. Không push/chạy với production secret. Tự test prompt injection,
one-lane failure, fork-event secret isolation, permissions, timeout và metric
labels. Tạo local report bằng fixtures; kết thúc PASS/BLOCKED.
```

### Chat 25 — Claude Code — Controlled DRAFT generator và human review contract

- **Mục tiêu:** tạo URS/DQ/IQ/OQ/PQ/Risk/TM/Deviation/SOP Review ở trạng thái DRAFT có citation.
- **Phạm vi file:** immutable `prompts/google-doc-draft/vN.md`, `n8n/workflows/TKTL-WF-03-draft-protocol.json`, templates và review/state tests.
- **Việc làm:** template/prompt version; source chunk mapping; disclaimer; `DRAFT→REVIEW→APPROVED/REJECTED`; creator/reviewer separation; snapshot request contract; generated record ghi `prompt_version`.
- **Tự kiểm:** critical paragraphs cited; no-source section blocked; AI/service cannot approve; invalid transition/reviewer=self denied.
- **DoD:** một equipment fixture tạo đủ một DRAFT/review package local; citation and state tests PASS.
- **Rollback:** disable generator; retain drafts/reviews/audit.

```text
Bạn là Claude Code, owner Chat 25. Xây prompt/template và source-only WF-03 cho
controlled DRAFT có citation và human review. Không update/run/publish n8n.
Tự test state transitions, creator!=reviewer, AI no-approve, no-source, critical
citation và invalid model output; JSON/secret scan/diff. Kết thúc PASS/BLOCKED.
```

### System Check S5 — Claude Code — Sau Chat 21–25

- **Phạm vi:** deterministic/Ragas/DeepEval/Promptfoo gate và DRAFT generator.
- **Bắt buộc kiểm:** 50–100 dataset version; metric semantics; four-lane fail behavior; DRAFT citation/state controls; no secret/data leakage.
- **Đầu ra:** `docs/checkpoints/system-check-S5.md` và `GO CYCLE 6`/`HOLD`.

```text
Bạn là Claude Code, owner System Check S5. Chạy tích hợp fixture/local cho Chat
21–25; xác nhận 4 eval lane độc lập và consolidated gate, metric đúng nghĩa,
failure injection, DRAFT citation/state/human review. Secret/data scan và source-
runtime drift read-only. Tạo system-check-S5.md; không live mutation/push.
```

## 11. Chu kỳ 6 — Google Docs, frontend, backup và validation

### Chat 26 — Claude Code — Google credential governance và OAuth OQ

- **Mục tiêu:** chốt account/project/scopes/folder/owner/revoke trước khi tạo hoặc bind credential.
- **Phạm vi file:** ADR credential boundary, credential inventory template, OAuth/OQ protocol, incident/rotation runbook.
- **Việc làm:** đối chiếu credential Google hiện có; chọn reuse hoặc `CRAVE-Google-Workspace`; scope tối thiểu Drive/Docs; sandbox folder; owner/recovery; Tavily tách riêng.
- **Tự kiểm:** folder-in/folder-out, create/update DRAFT, revoke fail-safe, token absent logs; không auto-approve/delete bulk.
- **DoD source:** governance/OQ được duyệt; thao tác tạo/bind credential được liệt kê chính xác.
- **Cổng live:** dù đã được chấp thuận về nguyên tắc, dừng và xin xác nhận ngay trước khi tạo/rebind OAuth thật; không publish workflow trong Chat này.
- **Rollback:** revoke credential/client, remove binding, preserve audit/runbook.

```text
Bạn là Claude Code, owner Chat 26. Inspect read-only Google credential bindings
của TKTL và tạo ADR/inventory/OAuth OQ/runbook. Ưu tiên least privilege và account
CRAVE riêng; Tavily tách biệt. Không tự tạo/rebind credential hoặc publish. Tự
kiểm scope/folder/revoke/log leakage và đưa kế hoạch live cụ thể để xin xác nhận.
Kết thúc READY FOR LIVE APPROVAL hoặc BLOCKED.
```

### Chat 27 — Codex GPT — WF-16 Google Docs DRAFT export

- **Mục tiêu:** export `generated_docs` DRAFT sang Google Docs mà giữ citation, template, state và trace.
- **Phạm vi file:** `n8n/workflows/TKTL-WF-16-google-docs-draft-export.json`, workflow docs, test payloads/mock và export mapping.
- **Việc làm:** create/update only DRAFT; restricted folder; external ID/URL; formatting/citation; PDF snapshot/hash callback; idempotent retry.
- **Tự kiểm:** JSON parse; no credential material; mock create/update/retry/revoke; cannot approve/delete; audit events; JWT Cách B.
- **DoD:** source/mock PASS; actual binding/import/publish chỉ sau xác nhận riêng.
- **Rollback:** disable export; keep Supabase DRAFT; revoke Google binding.

```text
Bạn là Codex GPT, owner Chat 27. Tạo source-only WF-16 Google Docs DRAFT export
theo approved ADR/OQ Chat 26. Không import/update/run/publish hoặc nhúng OAuth.
Tự test mock create/update/idempotency/revoke/folder boundary/citation/snapshot,
AI no-approve, audit/JWT/secret scan. Kết thúc PASS/BLOCKED hoặc READY FOR LIVE
APPROVAL với exact live steps.
```

### Chat 28 — Claude Code — Frontend document draft/review/evidence UI

- **Mục tiêu:** người dùng tạo/xem DRAFT, citation, review và snapshot mà frontend không có backend secret.
- **Phạm vi file:** `app/` components/routes/API client/tests; không move sang `frontend/app/` trong Chat này.
- **Việc làm:** state badges/disclaimer; source drawer; review controls theo role; pending/error/access-denied states; safe rendering.
- **Tự kiểm:** TypeScript/build/lint; XSS; anon key only; user cannot forge role/user_id; accessibility/mobile; API errors.
- **DoD:** UI fixture/smoke PASS; no service/OpenAI/Google/Tavily secret; no `innerHTML` unsafe.
- **Rollback:** feature flag/route removal; no DB data deletion.

```text
Bạn là Claude Code, owner Chat 28. Xây frontend React/TypeScript cho DRAFT,
citation, review và evidence trong app/, không move path. Không deploy/push.
Tự chạy build/lint/tests, XSS/role/user_id/error/mobile/accessibility checks và
secret scan. Frontend chỉ anon/publishable config. Kết thúc PASS/BLOCKED.
```

### Chat 29 — Codex GPT — Audit export, backup/restore và periodic review

- **Mục tiêu:** có thể xuất evidence, phục hồi và review định kỳ mà không sửa lịch sử.
- **Phạm vi file:** `scripts/export-audit/`, `scripts/backup/`, `docs/sop/backup-restore.md`, `periodic-review.md`, test fixtures.
- **Việc làm:** redacted append-only export, manifest/hash; backup scope; restore sandbox rehearsal; RPO/RTO proposal; access/workflow/prompt/model/advisor review.
- **Tự kiểm:** export hash verify; restore fixture; mutation audit denied; secret/redaction; failure/retry; storage retention.
- **DoD:** local rehearsal PASS; đề xuất RPO 24h/RTO 8h chờ business approval.
- **Rollback:** stop scheduler/export; preserve existing evidence; never delete audit.

```text
Bạn là Codex GPT, owner Chat 29. Tạo audit export, backup/restore và periodic
review source/runbooks với fixtures, không truy xuất/ghi production hoặc cài
scheduler live. Tự test hash/restore/redaction/failure, append-only và no-secret;
ghi RPO/RTO assumption. Kết thúc PASS/BLOCKED.
```

### Chat 30 — Claude Code — IQ/OQ/PQ, traceability matrix và P0 go/no-go

- **Mục tiêu:** đóng validation package P0 dựa trên evidence thật, không tuyên bố compliance quá mức.
- **Phạm vi file:** `docs/validation/urs.md`, `risk-assessment.md`, `iq.md`, `oq.md`, `pq.md`, `traceability-matrix.md`, release report.
- **Việc làm:** map requirement→risk→design→test→evidence; open deviations/CAPA; intended use; Part 11/Annex 11 boundary; release versions.
- **Tự kiểm:** every P0 requirement traced; evidence exists/not merely planned; draft regulation labelled draft; signatures not claimed from hash alone.
- **DoD:** go/no-go checklist rõ; unresolved P0 automatically NO-GO/HOLD.
- **Rollback:** validation docs versioned; correction by new version, not overwrite approved evidence.

```text
Bạn là Claude Code, owner Chat 30. Hoàn thiện P0 validation package từ source và
evidence thực tế, không biến planned test thành PASS. Tự kiểm traceability 100%,
risks/deviations/CAPA, intended use, Part 11/Annex 11 claims và release versions.
Không apply/publish/push. Kết thúc GO/NO-GO/HOLD có lý do và evidence paths.
```

### System Check S6 — Codex GPT — Sau Chat 26–30

- **Phạm vi:** credential governance, Docs export, frontend, backup/audit và validation package.
- **Bắt buộc kiểm:** live credential/workflow/settings chỉ đổi khi có recorded approval; citation survives export; frontend no secret; restore evidence; traceability/no-go rules.
- **Đầu ra:** `docs/checkpoints/system-check-S6.md` và quyết định P0 `GO`, `CONDITIONAL GO` hoặc `HOLD`.

```text
Bạn là Codex GPT, owner System Check S6. Kiểm tích hợp read-only Chat 26–30 và
toàn P0. Đối chiếu source/live approvals, credential binding, workflow versions,
frontend build, export/restore evidence và IQ/OQ/PQ traceability. Secret scan;
không thay live/push. Tạo system-check-S6.md với GO/CONDITIONAL GO/HOLD.
```

## 12. Chu kỳ 7 — P1 controlled intelligence và platform hardening

Chỉ bắt đầu chu kỳ 7 khi System Check S6 không còn P0 blocker. Mọi feature P1 có feature flag và đường quay về deterministic P0.

### Chat 31 — Codex GPT — Glossary governance UI

- **Mục tiêu:** domain owner đề xuất, duyệt, version và tra source cho thuật ngữ EN–VI.
- **Phạm vi file:** `app/` glossary pages/components/API/tests; glossary prompt display; không đổi schema ngoài 027.
- **Việc làm:** proposal/review/diff/source/status/effective version; role-based actions; approved-only consumption indicator.
- **Tự kiểm:** 100-term fixture; RLS/role; term chưa duyệt không dùng; XSS; build/mobile/accessibility; no secret.
- **DoD:** propose→review→approved/superseded fixture PASS; rollback active version test.
- **Rollback:** hide UI route/feature flag; keep glossary history.

```text
Bạn là Codex GPT, owner Chat 31. Xây glossary governance UI trong app/ theo schema
027, không deploy/push hoặc đổi live. Tự test 100 term fixture, role/RLS, approved-
only, version rollback, XSS/build/mobile/accessibility và secret scan. Kết thúc
PASS/BLOCKED.
```

### Chat 32 — Claude Code — AI Reviewer có citation

- **Mục tiêu:** phát hiện thiếu sót draft theo checklist nhưng không kết luận thay QA.
- **Phạm vi file:** immutable `prompts/ai-reviewer/vN.md`, `n8n/workflows/TKTL-WF-04-check-protocol.json`, finding schema và calibration/eval fixtures.
- **Việc làm:** severity/rule/checklist/source chunk/recommendation; reviewer disclaimer; human disposition; prompt/model/checklist versions được ghi vào finding/eval/log.
- **Tự kiểm:** every critical finding cited; unsupported finding blocked; false positive/negative calibration; AI cannot approve; injection.
- **DoD:** QA-labelled sample đạt acceptance mục tiêu đã calibration; 100% critical finding có source.
- **Rollback:** disable reviewer flag; human review remains canonical.

```text
Bạn là Claude Code, owner Chat 32. Xây AI Reviewer prompt/schema và WF-04 source-
only có citation/checklist version/human disposition. Không run/publish live.
Tự test unsupported findings, citation 100% critical, calibration false positive/
negative, injection và AI no-approve; JSON/secret scan. Kết thúc PASS/BLOCKED.
```

### Chat 33 — Codex GPT — WF-12 Controlled Agent

- **Mục tiêu:** agent hẹp chỉ dùng tool đã phê duyệt và mọi tool call được trace.
- **Phạm vi file:** `n8n/workflows/TKTL-WF-12-controlled-ai-agent.json`, immutable `prompts/controlled-agent/vN.md`, tool contracts và red-team tests.
- **Việc làm:** allowlist search/source/draft/calculate/checklist/log; per-tool auth; max 3–5 iterations; no arbitrary HTTP/shell/community node; no approval tool.
- **Tự kiểm:** tool injection, loop/budget, unauthorized tool, user identity, no-source, 100% tool call log, kill switch.
- **DoD:** red-team PASS và deterministic fallback; chưa publish/run.
- **Rollback:** feature flag to deterministic flows; retain logs.

```text
Bạn là Codex GPT, owner Chat 33. Nâng WF-12 source-only thành controlled agent có
tool allowlist/per-tool auth/max iteration/logs/kill switch. Không update/run/
publish. Không arbitrary HTTP/shell/community node hoặc approve tool. Tự red-team
injection/loop/identity/no-source/log coverage, parse JSON và secret scan.
Kết thúc PASS/BLOCKED.
```

### Chat 34 — Claude Code — Observability và review dashboard

- **Mục tiêu:** owner thấy ingest errors, citation, eval, latency/cost và review backlog từ nguồn có kiểm soát.
- **Phạm vi file:** read-only view/RPC source, `app/` dashboard, metric definitions/tests.
- **Việc làm:** filters release/workflow/prompt/model; trace drill-down redacted; metric semantic labels; cache/staleness display.
- **Tự kiểm:** widget totals match source queries; RLS cross-user; p95 query budget; frontend no service key; stale/error states.
- **DoD:** 100% widget reconciliation trên fixture; no sensitive drill-down leak.
- **Rollback:** hide route/panel; source logs remain.

```text
Bạn là Claude Code, owner Chat 34. Xây dashboard read-only/RLS-aware bằng source
views/RPC và app components, không apply/deploy/push. Tự đối soát mọi widget,
metric semantics, cross-user RLS, p95, stale/error/XSS và no service key. Kết thúc
PASS/BLOCKED với migration source nếu cần nhưng chưa apply.
```

### Chat 35 — Codex GPT — GitHub supply chain, frontend move và dependency upgrade

- **Mục tiêu:** pin supply chain, xử lý Vite/esbuild advisory và chuyển cây đích `frontend/app/` trong một change riêng có rollback.
- **Phạm vi file:** `.github/`, dependency manifests, build config, path move; không migration/n8n.
- **Việc làm:** pin action SHA, least permissions, CodeQL/Dependabot phù hợp; move one canonical frontend; update Pages base/import/cache; upgrade package theo changelog.
- **Tự kiểm:** clean install/build/lint/smoke; Pages preview/base/404; lockfile pair; fork events; secret scan; rollback deploy.
- **DoD:** CI/local PASS, một frontend canon, advisory decision recorded; chưa push/deploy.
- **Rollback:** atomic revert path/config/package+lock; previous Pages artifact.

```text
Bạn là Codex GPT, owner Chat 35. Làm một source change riêng cho supply-chain,
frontend app/→frontend/app/ và dependency upgrade; không đụng Supabase/n8n hoặc
deploy/push. Tự clean-build/lint/smoke/Pages base/404/fork permissions/lockfile/
secret scan và rollback rehearsal. Kết thúc PASS/BLOCKED.
```

### System Check S7 — Claude Code — Sau Chat 31–35

- **Phạm vi:** glossary UI, AI reviewer, controlled agent, dashboard và GitHub/frontend hardening.
- **Bắt buộc kiểm:** P0 controls không regression; AI no-approve; tool/citation logs; one frontend canon; supply-chain/CI; feature flags/rollback.
- **Đầu ra:** `docs/checkpoints/system-check-S7.md` và `GO CYCLE 8`/`HOLD`.

```text
Bạn là Claude Code, owner System Check S7. Kiểm tích hợp read-only/local Chat
31–35, đặc biệt no-approve, agent tools/logs, glossary approved-only, dashboard
RLS, frontend canon/build và CI supply chain. Secret scan/source-runtime drift;
không live mutation/push. Tạo system-check-S7.md và GO/HOLD.
```

## 13. Chu kỳ 8 — P2 chỉ khi có bằng chứng nhu cầu

Không bắt đầu P2 chỉ để tăng độ phức tạp. Mỗi Chat phải có ADR chứng minh P0/P1 hiện tại không đáp ứng được yêu cầu đo được.

### Chat 36 — Claude Code — Equipment Knowledge Graph

- **Mục tiêu:** liên kết equipment–document–requirement–test có provenance/version/approval.
- **Phạm vi file:** relationship migration source, graph query view/function, proposal/approval UI or workflow, tests/ADR.
- **Việc làm:** typed edges, source chunk, effective/version/status, AI proposes DRAFT edge only; human approval; orphan/cycle/business rules.
- **Tự kiểm:** 100% approved edge có source/owner/version; RLS graph traversal; no inferred GMP edge auto-approved.
- **DoD:** fixture graph queries PASS và business owner approves intended use.
- **Rollback:** disable graph features; preserve registry and edge history.

```text
Bạn là Claude Code, owner Chat 36. Chỉ làm Equipment Knowledge Graph nếu ADR có
evidence nhu cầu. Tạo source migration/query/UI-workflow/tests, không apply/live.
AI chỉ đề xuất DRAFT edge. Tự test provenance/version/approval, orphan/cycle,
graph RLS và rollback; secret scan. Kết thúc PASS/BLOCKED.
```

### Chat 37 — Codex GPT — Semantic cache có version và access scope

- **Mục tiêu:** giảm latency/chi phí mà không trả output stale hoặc rò giữa user.
- **Phạm vi file:** cache ADR/source/migration if needed, cache module/workflow stage, invalidation/security tests.
- **Việc làm:** key gồm normalized query + permission scope + document/prompt/model/glossary/release versions; TTL; high-risk bypass; trace hit/miss.
- **Tự kiểm:** cross-user collision, version invalidation, revoked access, stale doc, sensitive output, benchmark.
- **DoD:** 0 cache leakage; invalidation 100%; measured latency/cost benefit.
- **Rollback:** feature flag off and cache purge; audit unchanged.

```text
Bạn là Codex GPT, owner Chat 37. Chỉ triển khai semantic cache source local nếu
ADR/benchmark chứng minh nhu cầu. Cache key phải access+document+prompt+model+
glossary+release versioned; high-risk bypass. Tự test cross-user/revoke/stale/
invalidation/leak/benchmark, không apply/run live. Kết thúc PASS/BLOCKED.
```

### Chat 38 — Claude Code — Vector scaling dựa trên benchmark

- **Mục tiêu:** giữ recall/latency khi corpus tăng, không tách vector DB theo cảm tính.
- **Phạm vi file:** benchmark harness/report, index migration source/rollback, scale ADR.
- **Việc làm:** query plan, corpus-size simulation, HNSW/IVFFlat parameters, backfill/concurrency/resource; chỉ đề xuất partition/external DB khi evidence đủ.
- **Tự kiểm:** recall/Hit@k/p50/p95/cost before-after; index build lock/resource; rollback/zero-downtime.
- **DoD:** measurable benefit without gate regression; capacity threshold documented.
- **Rollback:** previous index/function config; drop new index only by reviewed migration.

```text
Bạn là Claude Code, owner Chat 38. Benchmark vector scaling trước khi đề xuất
index/partition/vector DB. Chỉ tạo harness/report/source migration, không apply.
Tự test recall/Hit@k/p95/cost/resource/locking/rollback và compare query plans.
Không đổi kiến trúc nếu evidence không đủ; kết thúc PASS/BLOCKED/NO-CHANGE.
```

### Chat 39 — Codex GPT — Advanced observability ADR/PoC

- **Mục tiêu:** chỉ bổ sung Langfuse/OpenLLMetry khi Supabase logs không đáp ứng use case cụ thể.
- **Phạm vi file:** ADR, data-flow/threat model, local PoC với dữ liệu giả, exporter config/tests.
- **Việc làm:** egress/redaction/sampling/retention/DPA boundary; trace correlation; outage fail-safe; internal audit remains canonical.
- **Tự kiểm:** no GMP/PII egress in PoC; secret storage; exporter outage; cost/cardinality; deletion/retention claims.
- **DoD:** ADR approve/reject dựa trên evidence; PoC không production.
- **Rollback:** disable exporter; no effect on internal audit.

```text
Bạn là Codex GPT, owner Chat 39. Làm ADR/threat model/local PoC advanced
observability chỉ với dữ liệu giả. Không gửi GMP/PII hoặc kết nối production.
Tự test redaction/egress/outage/secret/cost/retention và giữ Supabase audit là
canon. Kết thúc APPROVE/REJECT/HOLD có evidence.
```

### Chat 40 — Claude Code — Local auxiliary LLM evaluation

- **Mục tiêu:** đánh giá local LLM cho tác vụ phụ trợ, không thay model chính cho output controlled khi chưa validation.
- **Phạm vi file:** hardware/security/license ADR, local benchmark/eval config, model artifact manifest/hash, fallback tests.
- **Việc làm:** use cases classify/normalize/draft auxiliary; model pin/license/supply chain; isolated endpoint; resource/latency; primary controlled fallback.
- **Tự kiểm:** golden eval, hallucination/no-source, sandbox/egress, artifact integrity, hardware drift, fallback.
- **DoD:** decision `ADOPT LIMITED`, `REJECT` hoặc `REASSESS`; intended use explicit.
- **Rollback:** disable local route; controlled primary path retained.

```text
Bạn là Claude Code, owner Chat 40. Đánh giá local auxiliary LLM bằng ADR/benchmark
dữ liệu giả, không nối production hoặc thay primary model. Pin model/hash/license,
isolate endpoint và define narrow intended use. Tự test golden quality, no-source,
security/egress/resource/hardware drift/fallback. Kết thúc ADOPT LIMITED/REJECT/
REASSESS có evidence.
```

### System Check S8 — Codex GPT — Sau Chat 36–40

- **Phạm vi:** knowledge graph, semantic cache, vector scaling, advanced observability và local LLM.
- **Bắt buộc kiểm:** mỗi P2 có evidence nhu cầu; không regression security/GMP; no new uncontrolled egress/secret; rollback/feature flags; cost/operability.
- **Đầu ra:** `docs/checkpoints/system-check-S8.md` và final platform decision.

```text
Bạn là Codex GPT, owner System Check S8. Kiểm read-only/local toàn P2 Chat 36–40.
Yêu cầu evidence nhu cầu/benefit, no security/RLS/audit/citation regression, no
uncontrolled egress, secret scan, feature flags và rollback. Không live mutation/
push. Tạo system-check-S8.md và quyết định ADOPT/DEFER/REJECT từng P2.
```

## 14. Bảng theo dõi trạng thái Chat

### 14.1 Trạng thái hiện tại trước khi chạy Chat 01

- [x] **Đã hoàn thành:** kiểm tra chỉ đọc GitHub, Supabase và nhóm workflow TKTL n8n ngày 2026-06-28; bằng chứng/tóm tắt nằm trong `nangcap.md`.
- [x] **Đã hoàn thành:** lập roadmap kiến trúc, P0/P1/P2, schema, workflow mapping, credential decision và kế hoạch 12 tuần trong `nangcap.md`.
- [x] **Đã hoàn thành:** lập `kehoach.md` với 40 Chat chia đều Codex GPT/Claude Code và 8 System Check sau mỗi nhóm 5 Chat.
- [x] **Đã hoàn thành:** cập nhật mô hình hai người cùng xây, mỗi người tự kiểm; bỏ mô hình Codex viết rồi Claude review mặc định.
- [x] **Đã hoàn thành:** bổ sung sáu nguyên tắc GitHub-first, rollback, workflow export, prompt versioning, eval gate và sổ trạng thái.
- [ ] **Kế hoạch:** chạy Chat 01–40 và S1–S8 theo dependency; hiện chưa Chat triển khai nào được đánh dấu PASS.
- [!] **Chưa giải quyết:** `nangcap.md` và `kehoach.md` đang ở local/untracked, chưa có GitHub Issue, branch, commit, PR, merge hoặc release manifest entry.
- [!] **Chưa giải quyết:** `SUPABASE_SERVICE_ROLE_KEY` còn ở GitHub Variables, Secrets trống và `main` chưa protected.
- [!] **Chưa giải quyết:** production đã tới migration 022 nhưng source/rollback/baseline chưa đầy đủ; convention rollback mới chưa được CI enforce.
- [!] **Chưa giải quyết:** n8n live có 14 workflow nhưng Git mới có 5 JSON; WF-14 draft/published drift và literal Tavily secret cần xử lý/rotate.
- [!] **Chưa giải quyết:** 12/12 document thiếu file hash, 65/65 chunk thiếu embedding, chưa có Docling và Google Docs DRAFT flow.
- [!] **Chưa giải quyết:** `document_access` chưa có dữ liệu kiểm thử, citation/audit end-to-end chưa có bằng chứng, eval hiện mới chứng minh FTS retrieval.

### 14.2 Sổ trạng thái từng Chat

Ký hiệu: `✅` đã hoàn thành có evidence; `🗓️` kế hoạch/chưa bắt đầu; `⚠️` chưa giải quyết hoặc dependency phải đóng. Tất cả Chat dưới đây hiện là kế hoạch vì chưa được thực thi.

| Chat | Owner | Trạng thái | Đã hoàn thành | Kế hoạch | Chưa giải quyết/dependency |
|---:|---|---|---|---|---|
| 01 | Codex GPT | ✅ PASS | Snapshot/change register/file ownership đã vào `main` qua PR #3 merge `7fd1db5` | Không mở lại baseline; chỉ cập nhật evidence bằng change register | Issue riêng cho Chat 01 không có; chấp nhận hồi tố trong S1 |
| 02 | Claude Code | ✅ PASS với caveat | GitHub secret/branch hardening source có trên `main`; branch protection hiện yêu cầu PR + `TypeScript Build & Lint` | Chuẩn hóa policy single-owner/admin bypass nếu tiếp tục main-only | Provenance Issue/PR ban đầu chưa đầy đủ; `enforce_admins=false` |
| 03 | Codex GPT | ⚠️ BLOCKED | Supabase source tới 022 và source map đã vào `main`; S1 read-only verified live head `022` | Remediate/accept `run_fts_eval_v1` security drift và rollback/change-control 013–021d | Live thiếu `016`, `021c` name drift, `run_fts_eval_v1` search_path/grant drift, rollback `021d` unsafe |
| 04 | Claude Code | ✅ PASS với caveat | 14 workflow TKTL export/redaction/manifest; n8n live/source 14/14 khớp; WF-14 drift đã remediation | Cập nhật/đóng Issue #2 sau quyết định governance | Issue #2 còn OPEN/stale body; JWT byte-identical toàn hệ thống chưa chứng minh |
| 05 | Codex GPT | ✅ PASS | Issue/PR templates, repo scaffold, release validator và CI guardrail đã vào `main`; CI remediation `5fb904a` PASS | Cân nhắc đưa release guard vào required checks bằng change riêng | CI required context đã PASS trên push; cần quan sát PR kế tiếp để chứng minh pull_request path |
| S1 | Claude Code / Codex GPT | ⚠️ HOLD | `docs/checkpoints/system-check-S1.md`; CI remediation PASS run `28343429940`; Supabase read-only evidence lập; migration 023 source package lập | Apply/verify `023_harden_run_fts_eval_v1`, đóng rollback/change-control, Issue #2 và WF-06 | Chưa GO CYCLE 2 |
| 06 | Codex GPT | ⚠️ BLOCKED | — | Migration 023 security/eval hardening | Phụ thuộc S1 GO và exact live signatures; chưa apply |
| 07 | Claude Code | 🗓️ KẾ HOẠCH | — | Docling local spike 5 file | Chưa chốt fixture/parser/version/resource baseline |
| 08 | Claude Code | 🗓️ KẾ HOẠCH | — | Docling worker + OQ 20 file | Phụ thuộc kết quả Chat 07; chưa có production connector |
| 09 | Codex GPT | 🗓️ KẾ HOẠCH | — | Migration 024: document versions + `version_status`/`newer_version_url`/RPC | Phụ thuộc 022/023 source và backfill mapping 12 docs/65 chunks |
| 10 | Codex GPT | 🗓️ KẾ HOẠCH | — | WF-10/WF-15/WF-01 ingestion contract/export | Phụ thuộc manifest Chat 08 và schema 024; chưa import/publish |
| 11 | Codex GPT | 🗓️ KẾ HOẠCH | — | Chunking/embedding pipeline | Corpus hiện 0/65 embedding; release phải chờ eval gate Chat 21–24 |
| 12 | Claude Code | 🗓️ KẾ HOẠCH | — | Migration 025 observability | Event fields/grants/retention chưa chốt; chưa apply |
| 13 | Claude Code | 🗓️ KẾ HOẠCH | — | Audit event/trace contract | Phụ thuộc 025; event exactly-once/redaction chưa test |
| 14 | Codex GPT | 🗓️ KẾ HOẠCH | — | Migration 026 generated docs/reviews | Mapping bảng cũ và segregation of duties chưa dry-run |
| 15 | Claude Code | 🗓️ KẾ HOẠCH | — | Migration 027 glossary/equipment | Glossary canon/compatibility và P2 relationship gate chưa chốt |
| 16 | Codex GPT | 🗓️ KẾ HOẠCH | — | Harden `hybrid_search_v3` | Phụ thuộc schema 024/025/027 và eval gate trước release |
| 17 | Claude Code | 🗓️ KẾ HOẠCH | — | Versioned query/glossary VI→EN/rerank prompt | Cần approved glossary và prompt `vN`; chưa calibration |
| 18 | Codex GPT | 🗓️ KẾ HOẠCH | — | Export WF-02 + versioned citation prompt | Citation/no-source/RLS chưa đạt gate; chưa publish |
| 19 | Claude Code | 🗓️ KẾ HOẠCH | — | RLS/JWT/injection negative suite | Thiếu two-user fixtures và intentional-failure evidence |
| 20 | Codex GPT | 🗓️ KẾ HOẠCH | — | Export instrumented workflow/log subflow | Phụ thuộc event matrix; retry/exactly-once chưa kiểm |
| 21 | Claude Code | 🗓️ KẾ HOẠCH | — | Deterministic retrieval eval + golden 50–100 | Metric cũ đang dùng sai nghĩa; dataset/owner/version chưa khóa |
| 22 | Codex GPT | 🗓️ KẾ HOẠCH | — | Ragas lane | Judge calibration/cost/variance chưa xác lập |
| 23 | Claude Code | 🗓️ KẾ HOẠCH | — | DeepEval custom GMP lane | Custom assertions/dependency lock chưa có |
| 24 | Codex GPT | 🗓️ KẾ HOẠCH | — | Promptfoo + consolidated release gate | Chưa có output đủ từ 21–23; CI secret isolation chưa test |
| 25 | Claude Code | 🗓️ KẾ HOẠCH | — | Export WF-03 + versioned Google-doc DRAFT prompt | Phụ thuộc 026, citations và eval gate; chưa publish |
| 26 | Claude Code | 🗓️ KẾ HOẠCH | — | Google credential governance/OAuth OQ | Chưa chọn reuse/new credential, scopes/folder; live action chờ xác nhận |
| 27 | Codex GPT | 🗓️ KẾ HOẠCH | — | Export WF-16 Google Docs DRAFT | Phụ thuộc OQ/credential approval; chưa import/bind/publish |
| 28 | Claude Code | 🗓️ KẾ HOẠCH | — | Frontend DRAFT/review/evidence | Phụ thuộc API/workflow contracts; chưa deploy |
| 29 | Codex GPT | 🗓️ KẾ HOẠCH | — | Audit export/backup/restore/periodic review | RPO/RTO và restore environment chưa được business phê duyệt |
| 30 | Claude Code | 🗓️ KẾ HOẠCH | — | IQ/OQ/PQ/traceability/P0 go-no-go | Phụ thuộc evidence thật từ 01–29; planned test không được tính PASS |
| 31 | Codex GPT | 🗓️ KẾ HOẠCH | — | Glossary governance UI | Chỉ bắt đầu sau S6; phụ thuộc 027 và approved workflow |
| 32 | Claude Code | 🗓️ KẾ HOẠCH | — | Export WF-04 + versioned AI reviewer prompt | Chỉ P1; calibration/QA acceptance chưa có |
| 33 | Codex GPT | 🗓️ KẾ HOẠCH | — | Export WF-12 + versioned controlled-agent prompt | Tool allowlist/log/red-team chưa PASS; không publish trước P0 |
| 34 | Claude Code | 🗓️ KẾ HOẠCH | — | Observability/review dashboard | View/RPC/RLS/metric semantics chưa thiết kế |
| 35 | Codex GPT | 🗓️ KẾ HOẠCH | — | Supply chain, frontend move, dependency upgrade | Chỉ làm change riêng; Pages/base/rollback chưa test |
| 36 | Claude Code | 🗓️ KẾ HOẠCH | — | Equipment Knowledge Graph | P2, cần evidence nhu cầu và approved-source policy |
| 37 | Codex GPT | 🗓️ KẾ HOẠCH | — | Semantic cache version/access scoped | P2, chưa có benchmark; leakage/invalidation risk |
| 38 | Claude Code | 🗓️ KẾ HOẠCH | — | Vector scaling benchmark | P2, corpus hiện quá nhỏ để kết luận kiến trúc |
| 39 | Codex GPT | 🗓️ KẾ HOẠCH | — | Advanced observability ADR/PoC | P2, egress/DPA/retention chưa được phê duyệt |
| 40 | Claude Code | 🗓️ KẾ HOẠCH | — | Local auxiliary LLM evaluation | P2, hardware/license/security/eval chưa đủ bằng chứng |

### 14.3 Quy tắc cập nhật sổ trạng thái

- Khi Chat bắt đầu: chuyển `🗓️ KẾ HOẠCH` thành `🔄 IN_PROGRESS`, ghi Issue và branch.
- Khi source/test hoàn tất nhưng chưa push/PR: dùng `⏸ READY_FOR_GITHUB_APPROVAL`.
- Khi PR/merge/release package xong nhưng thao tác live chưa được phép: dùng `⏸ READY_FOR_LIVE_APPROVAL`.
- Chỉ chuyển `✅ PASS` khi các ô Đã hoàn thành có evidence path, test/eval result, migration rollback/workflow export/prompt version phù hợp và không còn blocker critical.
- Nếu còn blocker: dùng `⚠️ BLOCKED`, giữ nguyên mục Chưa giải quyết với owner, impact, next action và review date.
- `DEFERRED` chỉ dùng khi có lý do/risk acceptance/owner/review date; không dùng để che test FAIL.

## 15. Mẫu báo cáo bắt buộc cuối mỗi Chat

```text
CHAT: [số và tên]
OWNER: [Codex GPT hoặc Claude Code]
STATUS: [IN_PROGRESS/PASS/BLOCKED/READY_FOR_GITHUB_APPROVAL/READY_FOR_LIVE_APPROVAL/DEFERRED]

GITHUB FLOW
- Issue: [URL/số hoặc Issue body local chờ tạo]
- Branch: [chat-XX/ten-ngan]
- Commit: [SHA hoặc chưa có]
- Pull Request: [URL/số hoặc PR checklist local]
- Merge/Release manifest: [SHA/version hoặc chưa có]

1. File tạo/sửa:
2. Migration và rollback pair: [đường dẫn/không áp dụng]
3. Workflow export JSON + manifest: [đường dẫn/không áp dụng]
4. Prompt version: [prompt key/vN/content hash/không áp dụng]
5. Test và eval gate: [lệnh, report, threshold, PASS/FAIL/BLOCKED]
6. Supabase thay đổi live: Không/Có — kèm approval/evidence
7. n8n thay đổi live: Không/Có — kèm approval/evidence
8. GitHub remote/settings thay đổi: Không/Có — kèm approval/evidence
9. Secret scan: PASS/FAIL
10. Rollback:
11. File ownership bàn giao cho Chat tiếp theo:
12. Có đủ điều kiện đi tiếp/release không: Có/Không

TRẠNG THÁI CÔNG VIỆC
- [x] Đã hoàn thành: [mỗi item kèm evidence path/test/commit hoặc local status]
- [ ] Kế hoạch tiếp theo: [owner, dependency, expected output]
- [!] Chưa giải quyết: [blocker/drift/test fail/approval; impact, owner, next action]
```

## 16. Những việc không được gộp vào một Chat

- Không gộp migration source với apply production.
- Không gộp workflow draft với import/publish/execute live.
- Không gộp credential creation/rebinding với workflow publish.
- Không bỏ qua GitHub Issue/branch/PR/merge/release manifest để sửa production trực tiếp.
- Không merge/apply migration khi thiếu rollback cùng số/tên trong `supabase/rollbacks/`.
- Không publish workflow khi JSON đã redaction chưa export vào GitHub branch/PR.
- Không sửa đè prompt version cũ hoặc release output không ghi `prompt_version`.
- Không release thay đổi prompt/retrieval/workflow/model quan trọng khi golden/eval gate FAIL hoặc chưa chạy.
- Không gộp migration + n8n + frontend deploy thành một release không rollback độc lập.
- Không gộp cả Ragas, DeepEval và Promptfoo vào một dependency change; ba lane riêng, hợp nhất ở release gate.
- Không gộp frontend path move/dependency major upgrade với P0 schema/workflow.
- Không để System Check tự sửa code để “làm xanh”; finding phải quay lại owner bằng Chat sửa lỗi riêng hoặc mở lại Chat gốc.
- Không gộp migration 023 (security/eval hardening) với migration 024 (document versions + version_status); hai migration khác nhau về risk, dependency và rollback.
- Không để một người vừa viết code vừa tự approve DoD mà không có evidence path rõ ràng (test result hoặc checklist); với nhóm <10 người, tự kiểm vẫn phải có output cụ thể có thể audit được.

## 17. Điều kiện kết thúc toàn kế hoạch

Kế hoạch chỉ được coi là hoàn tất khi:

- Tất cả Chat bắt buộc trong phạm vi được duyệt có trạng thái PASS hoặc DEFERRED có lý do/owner/review date.
- Tám System Check có báo cáo; không checkpoint nào bị bỏ qua chỉ vì unit tests xanh.
- Mọi thay đổi production có chuỗi truy nguyên `Issue → Branch → Commit → PR → Merge → Release manifest → Live evidence`.
- Mọi migration có forward/rollback pair cùng số/tên và CI đã xác nhận.
- Mọi workflow TKTL live có JSON đã redaction trong GitHub và manifest khớp `activeVersionId`.
- Mọi prompt production là version bất biến trong GitHub và output/eval/log ghi prompt version.
- Mọi thay đổi RAG/agent/model quan trọng qua golden questions và eval gate; không có waiver critical hết hạn.
- Git/source/live có traceable release manifest; mọi drift đã đóng hoặc được chấp nhận bằng change control.
- Không còn backend secret trong GitHub Variables/source/frontend/n8n CONFIG; credential có owner/scope/review/revoke record.
- RLS leakage = 0; no-source refusal = 100%; claim citation ≥95%; controlled chunks có hash/version/embedding 100%.
- Eval bốn lane và validation package phân biệt rõ planned, executed, PASS, FAIL và BLOCKED.
- AI không có quyền approve GMP records; audit/review evidence append-only.
- Mọi thao tác production đã có approval record, người thực hiện, timestamp, test evidence và rollback result.

> **Hai người cùng xây, mỗi người tự kiểm; hệ thống được kiểm tra tích hợp sau mỗi 5 Chat.**
