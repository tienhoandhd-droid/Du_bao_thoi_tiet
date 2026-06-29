# Change-control plan — rollback 013–021d

**Ngày lập:** 2026-06-29
**Phạm vi:** Supabase migration source từ `013` đến `021d` trong repo CRAVE
**Project đích:** `bdttccztjtrcaztjgkot`
**Trạng thái:** **HOLD — chưa đủ điều kiện GO CYCLE 2**

## 1. Mục tiêu

Tài liệu này không tạo rollback mới và không apply SQL. Mục tiêu là chốt cách xử
lý thiếu hụt rollback được System Check S1 phát hiện, để tránh việc “vá xanh” bằng
rollback suy đoán không có evidence.

Theo rule System Check, thiếu rollback tương ứng hoặc rollback không thể restore
đúng trạng thái trước migration là blocker release. Vì dữ liệu GMP/eval/audit có
thể đã phát sinh sau khi migration chạy, rollback phải được xem như change-control
riêng, không phải thao tác kỹ thuật tùy tiện.

## 2. Inventory hiện tại

| Migration | Source hiện có | Rollback hiện có | Nhận định |
|---|---|---|---|
| `013_citation_grounding.sql` | Có | `013_down.sql` trong `supabase/migrations/` | Có rollback theo convention cũ; cần canonical mapping hoặc di chuyển sang convention mới bằng change riêng. |
| `014_chat_memory.sql` | Có | `014_down.sql` trong `supabase/migrations/` | Có rollback theo convention cũ; cần kiểm dependency dữ liệu chat trước khi coi safe. |
| `015_platform_security_hardening.sql` | Có | `015_down.sql` trong `supabase/migrations/` | Có rollback nhưng cố ý khôi phục quyền cũ; cần risk acceptance vì có thể giảm security posture. |
| `016_eval_harness.sql` | Có | `016_down.sql` trong `supabase/migrations/` | Source map ghi live evidence chưa rõ vì live list từng thể hiện eval harness ở `021`; cần xác minh live trước mọi rename/apply. |
| `017_equipment_glossary.sql` | Có | `017_down.sql` trong `supabase/migrations/` | Có rollback theo convention cũ; cần kiểm dữ liệu regulated/seed trước khi drop. |
| `018_seed_validation_data.sql` | Có | `018_down.sql` trong `supabase/migrations/` | Rollback dữ liệu seed cần xác định owner và dữ liệu nào là fixture vs production. |
| `019_drive_sync_log.sql` | Có | `019_down.sql` trong `supabase/migrations/` | Có rollback theo convention cũ; cần retention decision cho log đồng bộ. |
| `020_validation_sessions.sql` | Có | `020_down.sql` trong `supabase/migrations/` | Có rollback theo convention cũ; cần retention decision cho validation session. |
| `021_eval_harness.sql` | Có | `021_down.sql` trong `supabase/migrations/` | `021_down` đang gộp rollback cho `021`, `021b`, `021c`, `021d`; không đạt convention one-to-one. |
| `021b_eval_function_v2.sql` | Có | Không có file riêng | **Blocker:** source v2 là superseded stub; rollback đúng cần biết predecessor và live order. |
| `021c_eval_function_v3.sql` | Có | Không có file riêng | **Blocker:** source map ghi name drift; rollback đúng cần exact function body trước `021c`. |
| `021d_eval_score_columns_fix.sql` | Có | Không có file riêng | **Blocker:** rollback score precision có trong `021_down`, nhưng chưa tách riêng; live `eval_runs` đang có `score_mean=96.55` và `score_min=81.03`, nên rollback về `numeric(5,4)` không an toàn. |

## 3. Quyết định change-control đề xuất

### 3.1 Không bịa rollback lịch sử

Không tạo rollback “ước lượng” cho `021b`, `021c`, `021d` nếu không có evidence
về trạng thái trước migration. Với function `run_fts_eval_v1`, rollback đúng không
chỉ là `DROP FUNCTION`: cần biết body, grants, owner, volatility, security definer
và search path của phiên bản trước đó.

### 3.2 Tách hai luồng xử lý

1. **Luồng canonical hóa source-only**
   - Mục tiêu: thống nhất naming/location rollback để CI có thể kiểm.
   - Chỉ áp dụng cho rollback đã có evidence nội dung trong repo (`013`–`021`).
   - Không đổi SQL runtime và không apply live.

2. **Luồng recovery evidence**
   - Mục tiêu: xác minh live và phục hồi evidence còn thiếu.
   - Áp dụng cho `016`, `021b`, `021c`, `021d`, `022`.
   - Cần Supabase read-only verification trước khi viết hoặc chấp nhận rollback.

### 3.3 Recovery rehearsal bắt buộc

Trước GO CYCLE 2, cần có ít nhất một trong hai bằng chứng:

- Restore rehearsal trên môi trường test/clone với migration chain và rollback
  tương ứng; hoặc
- Approved manual recovery package có owner, expiry, dữ liệu không được drop,
  và SQL read-only verification chứng minh trạng thái live khớp source.

## 4. Supabase read-only query pack cần chạy

Các truy vấn dưới đây là read-only. Không chạy trong S1 remediation này vì phiên
hiện tại không có Supabase MCP, `supabase` CLI, `psql`, hay biến kết nối DB.

```sql
-- 1. Live migration head và thứ tự migration.
select version, name, inserted_at
from supabase_migrations.schema_migrations
order by version;

-- 2. Function signatures/security-critical attributes.
select
  n.nspname as schema_name,
  p.proname as function_name,
  pg_get_function_identity_arguments(p.oid) as identity_arguments,
  p.prosecdef as security_definer,
  p.provolatile as volatility,
  pg_get_userbyid(p.proowner) as owner,
  p.proconfig as config
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in ('run_fts_eval_v1', 'hybrid_search_v3');

-- 3. Exact function definitions for evidence archive.
select
  n.nspname as schema_name,
  p.proname as function_name,
  pg_get_function_identity_arguments(p.oid) as identity_arguments,
  pg_get_functiondef(p.oid) as function_definition
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in ('run_fts_eval_v1', 'hybrid_search_v3');

-- 4. RLS/policies/grants cho bảng eval và documents.
select schemaname, tablename, rowsecurity, forcerowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('documents', 'document_chunks', 'eval_runs', 'eval_results', 'audit_log');

select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('documents', 'document_chunks', 'eval_runs', 'eval_results', 'audit_log')
order by tablename, policyname;

select table_schema, table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('documents', 'document_chunks', 'eval_runs', 'eval_results', 'audit_log')
order by table_name, grantee, privilege_type;

-- 5. Kiểm rủi ro rollback 021d trước khi thu hẹp numeric.
select
  max(score_mean) as max_score_mean,
  max(score_min) as max_score_min
from public.eval_runs;
```

## 5. Live evidence từ S1

S1 read-only verification ngày 2026-06-29 đã xác nhận:

- Live head tới `022`.
- Live thiếu `016` trong `schema_migrations`.
- Live `021c` có tên `021c_eval_function_v3_or_tsquery`, khác source filename.
- `run_fts_eval_v1` live là `SECURITY DEFINER`, executable bởi `anon`, và không
  có search_path config dù source `022` có `SET search_path = public, extensions`.
- `eval_runs` có `max(score_mean)=96.55`, `max(score_min)=81.03`, `count=10`;
  rollback `021d` về `numeric(5,4)` sẽ không an toàn nếu không xử lý dữ liệu.

Evidence chi tiết: `docs/checkpoints/s1-supabase-readonly-evidence.md`.

## 6. Điều kiện đóng blocker rollback

Blocker rollback 013–021d chỉ được đóng khi:

1. Có bảng mapping source ↔ live migration đã xác minh read-only.
2. Có convention rollback được chọn và enforce bằng CI/script.
3. `021b`, `021c`, `021d` có rollback riêng hoặc có approved manual recovery
   package với lý do không thể rollback tự động.
4. `016` vs `021` eval harness drift được giải thích bằng evidence, không đoán.
5. Rollback `022` có old definition hoặc được chấp nhận là manual restore với
   owner/expiry rõ ràng.
6. Secret scan và SQL parse/test PASS sau mọi thay đổi source.

## 7. Khuyến nghị trạng thái

Cho tới khi các điều kiện trên có evidence, mục rollback vẫn là:

**HOLD — không bắt đầu migration 023 như release bình thường.**
