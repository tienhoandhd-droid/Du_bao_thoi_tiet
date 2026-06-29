# S1 remediation — run_fts_eval_v1 hardening

**Ngày:** 2026-06-29
**Scope:** Supabase source package only
**Live operation:** applied after explicit approval
**Status:** **LIVE_APPLIED — PASS**

## 1. Finding được xử lý

S1 Supabase read-only verification xác nhận live `run_fts_eval_v1(integer,text,text)`:

- là `SECURITY DEFINER`;
- không có locked `search_path`;
- executable bởi `anon`;
- source `022_fix_eval_rank_order.sql` mong đợi function có `SET search_path`.

Đây là security drift đủ để giữ S1 ở HOLD.

## 2. Source package

| File | Mục đích |
|---|---|
| `supabase/migrations/023_harden_run_fts_eval_v1.sql` | Lock `search_path` và thu hồi execute khỏi `PUBLIC`/`anon`. |
| `supabase/rollbacks/023_harden_run_fts_eval_v1_down.sql` | Rollback có cảnh báo, khôi phục trạng thái insecure đã quan sát ở S1. |

## 3. Intended post-apply state

Sau khi được phê duyệt và apply live, trạng thái mong muốn:

| Attribute | Expected |
|---|---|
| Function | `public.run_fts_eval_v1(integer, text, text)` |
| `SECURITY DEFINER` | giữ nguyên |
| `search_path` | `pg_catalog, public, extensions` |
| Execute `anon` | false |
| Execute `authenticated` | true |
| Execute `service_role` | true |

Giữ `authenticated` vì frontend `EvalPanel` hiện gọi RPC cho manual eval khi user
đã đăng nhập. Giữ `service_role` vì GitHub Actions eval workflow gọi RPC bằng
`SUPABASE_SERVICE_ROLE_KEY`.

## 4. SQL verification pack sau apply

Chỉ chạy sau khi người dùng phê duyệt live apply:

```sql
select
  n.nspname as schema_name,
  p.proname as function_name,
  pg_get_function_identity_arguments(p.oid) as identity_arguments,
  p.prosecdef as security_definer,
  p.provolatile as volatility,
  pg_get_userbyid(p.proowner) as owner,
  coalesce(array_to_string(p.proconfig, '; '), '') as config
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'run_fts_eval_v1'
  and pg_get_function_identity_arguments(p.oid) = 'p_top_k integer, p_model_tag text, p_notes text';

select
  r.rolname as grantee,
  has_function_privilege(r.rolname, 'public.run_fts_eval_v1(integer,text,text)'::regprocedure, 'EXECUTE') as can_execute
from pg_roles r
where r.rolname in ('anon', 'authenticated', 'service_role', 'postgres')
order by r.rolname;
```

## 5. Risk còn lại

Migration 023 chỉ xử lý function security drift. Nó không đóng các S1 blockers còn lại:

- rollback `021d` vẫn unsafe với live `eval_runs` data;
- WF-06 direct SQL/DB credential boundary vẫn HOLD;
- Issue #2 governance vẫn cần update/close;
- migration `016`/`021c` history drift vẫn cần change-control explanation.

## 6. Live apply result

Migration 023 was applied live after explicit user confirmation. Post-apply
verification passed:

- `search_path=pg_catalog, public, extensions`;
- `anon` execute = false;
- `authenticated` execute = true;
- `service_role` execute = true;
- live migration record `20260629095000 / 023_harden_run_fts_eval_v1` exists.

Evidence: `docs/checkpoints/s1-run-fts-eval-live-apply.md`.

## 7. Quyết định

The `run_fts_eval_v1` security finding is remediated live.

**Không GO CYCLE 2 chỉ nhờ remediation này.** Cần xử lý các blocker còn lại.
