# CRAVE — Current-state snapshot

**Snapshot timestamp:** 2026-06-29 (Asia/Ho_Chi_Minh)<br>
**Phạm vi:** CRAVE / GMP Validation Intelligence Platform, Supabase `bdttccztjtrcaztjgkot`, workflow prefix `TKTL`<br>
**Loại bằng chứng:** ảnh chụp trạng thái đầu kỳ; không phải bằng chứng release hay quyền phê duyệt GMP

## 1. Nguồn và giới hạn xác minh

| Mã nguồn | Nguồn | Thời điểm | Phạm vi bằng chứng |
|---|---|---|---|
| `LIVE-PASTE-2026-06-29` | Nội dung live do người dùng paste vào Chat 01 | 2026-06-29 | Supabase, n8n, GitHub settings/Actions, credential inventory và known drift |
| `REPO-LOCAL-2026-06-29` | Repo local `tienhoandhd-droid/Du_bao_thoi_tiet` trên nhánh `main` | 2026-06-29 | Cây file, Git history, workflow/migration source đang có trong repo |
| `CANON-PLAN-2026-06-29` | [`AGENTS.md`](../../AGENTS.md), [`nangcap.md`](../../nangcap.md), [`kehoach.md`](../../kehoach.md) | Đọc ngày 2026-06-29 | Quy tắc an toàn, kiến trúc và Chat 01 card |

Codex không có MCP trong Chat này. Mọi dữ kiện “live” bên dưới được ghi lại từ `LIVE-PASTE-2026-06-29`, không được Codex truy vấn lại độc lập. Không có dữ liệu GMP thật hoặc giá trị secret nào được đưa vào snapshot.

## 2. Baseline định lượng

| Hạng mục | Trạng thái tại snapshot | Timestamp | Source |
|---|---:|---|---|
| Bảng Supabase | **33 bảng**, tất cả đã bật RLS | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Migration live | **001–022 đã apply**; phiên bản live cao nhất là **022** | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Workflow n8n TKTL | **14 workflow active**, từ WF-01 đến WF-14 | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Golden questions | **58 câu active** | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Document chunks | **65 chunks**, trong đó **0 embedding**; retrieval hiện là FTS-only | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Documents | **12 documents** | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Eval gần nhất | Hit@5 **96,55%**; MRR **0,8807** | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| PostgreSQL | **17.6** | 2026-06-29 | `LIVE-PASTE-2026-06-29` |

Các chỉ số eval trên là baseline FTS retrieval; chúng không tự chứng minh answer faithfulness, citation correctness hoặc trạng thái release của thay đổi sau snapshot.

## 3. Credential và biến cấu hình — chỉ tên, không có giá trị

### n8n

| Tên credential | Loại/mục đích được biết | Trạng thái tại snapshot | Source |
|---|---|---|---|
| `GMP-check` | Kết nối Postgres/Supabase cho workflow TKTL | Có trên n8n live | `LIVE-PASTE-2026-06-29` |
| `OpenAl` | OpenAI; ký tự cuối là chữ `l` thường | Có trên n8n live | `LIVE-PASTE-2026-06-29` |

Snapshot cố ý không ghi credential ID, token, key, password, OAuth material hoặc credential export. Inventory này chỉ phản ánh hai tên được cung cấp cho trạng thái live ngày 2026-06-29; không phải danh sách cho phép dài hạn thay thế `AGENTS.md`.

### GitHub Actions

| Phân loại | Tên | Trạng thái tại snapshot | Source |
|---|---|---|---|
| Repository Variable | `SUPABASE_ANON_KEY` | Có | `LIVE-PASTE-2026-06-29` |
| Repository Variable | `SUPABASE_URL` | Có | `LIVE-PASTE-2026-06-29` |
| Repository Variable | `WEBHOOK_BASE` | Có | `LIVE-PASTE-2026-06-29` |
| Repository Secret | `SUPABASE_SERVICE_ROLE_KEY` | Có; đã chuyển khỏi Variables trong Chat 02 | `LIVE-PASTE-2026-06-29` |

Chỉ tên biến/secret được ghi nhận. Snapshot không khẳng định nội dung hoặc tính đúng đắn của bất kỳ giá trị nào.

## 4. GitHub control plane

| Control | Trạng thái tại snapshot | Timestamp | Source |
|---|---|---|---|
| Default branch | `main` | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Branch protection | Đã bật: bắt buộc PR, CI phải pass, không cho force push | 2026-06-29 | `LIVE-PASTE-2026-06-29` |
| Eval workflow | [`.github/workflows/eval.yml`](../../.github/workflows/eval.yml) dùng `secrets.SUPABASE_SERVICE_ROLE_KEY` | 2026-06-29 | `LIVE-PASTE-2026-06-29` và `REPO-LOCAL-2026-06-29` |
| CI workflow | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) có trong repo | 2026-06-29 | `LIVE-PASTE-2026-06-29` và `REPO-LOCAL-2026-06-29` |
| Pages workflow | [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) có trong repo | 2026-06-29 | `LIVE-PASTE-2026-06-29` và `REPO-LOCAL-2026-06-29` |
| Repo HEAD quan sát được | `da1f5fb` trên local `main` | 2026-06-29 | `REPO-LOCAL-2026-06-29` |

## 5. Known drift và điểm chưa giải quyết

| ID | Drift / rủi ro | Bằng chứng tại 2026-06-29 | Ảnh hưởng | Owner / next action |
|---|---|---|---|---|
| `DRIFT-N8N-001` | **9/14 workflow TKTL chưa có JSON canonical trong repo**; repo chỉ có 5/14 bản export cũ | `LIVE-PASTE-2026-06-29`; repo local có 5 JSON tại `n8n/` | Không thể tái lập hoặc diff đầy đủ n8n live từ Git | Chat 04 (Claude): export/redact đủ workflow vào `n8n/workflows/`, lập docs và release manifest; không publish khi chưa được duyệt |
| `DRIFT-DB-001` | Migration **023+ chưa viết và chưa apply** | `LIVE-PASTE-2026-06-29` | Roadmap nâng cấp schema chưa bắt đầu; không được coi là lỗi production hiện tại | Chat 03 trở đi: reconcile source trước; migration mới bắt đầu từ 023 và chỉ apply sau phê duyệt live |
| `DRIFT-DB-002` | Live đã tới **022** nhưng repo local chỉ có migration source tới `021d`; thiếu source/rollback canonical của 022 | `LIVE-PASTE-2026-06-29` và `REPO-LOCAL-2026-06-29` | Source–runtime drift; restore/review chưa tái lập đầy đủ | Chat 03 (Codex): tạo baseline/source map và source/rollback 022 theo bằng chứng live được Claude cung cấp; không đoán definition |
| `RISK-N8N-001` | WF-14 **có thể** còn Tavily key literal trong CONFIG node; chưa được xác minh | `LIVE-PASTE-2026-06-29` | Nguy cơ lộ secret và vi phạm source governance | Chat 04 (Claude): inspect read-only, redaction và secret scan; nếu có secret thì HOLD và xử lý theo change control trước mọi publish |

## 6. Ranh giới sử dụng snapshot

- Snapshot này chỉ đóng băng baseline ngày 2026-06-29; mỗi thao tác release/live vẫn cần bằng chứng mới và phê duyệt riêng.
- Chỉ workflow prefix `TKTL` nằm trong phạm vi. Không kiểm tra hoặc thay đổi BMS-GMP, VMP, QMSTeam hay GMP Kiểm Tạp.
- Không có thao tác Supabase, n8n hoặc GitHub remote nào được thực hiện trong Chat 01.
- Thay đổi sau timestamp phải được ghi vào [`change-register.md`](../governance/change-register.md), không sửa ngược baseline để che drift lịch sử.
