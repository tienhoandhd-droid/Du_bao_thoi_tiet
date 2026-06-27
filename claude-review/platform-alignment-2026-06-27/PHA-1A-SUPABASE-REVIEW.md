# PHA 1A — Hướng dẫn review migration 015

## File cần review

- `supabase/migrations/015_platform_security_hardening.sql`
- `supabase/migrations/015_down.sql`

## Mục tiêu thay đổi

1. Ba view tài liệu chạy với `security_invoker=true`.
2. `anon` không được SELECT ba view trực tiếp.
3. Mười một nhóm RPC nhạy cảm không còn callable bởi `PUBLIC`, `anon` hoặc
   `authenticated`; `service_role` vẫn có EXECUTE cho backend được kiểm soát.
4. Mười bảy nhóm function có `search_path` cố định.
5. `audit_log` bỏ policy INSERT public và không còn API mutation grants.
6. `audit_log` và `chat_memory` có trigger chặn UPDATE/DELETE/TRUNCATE, kể cả khi
   caller dùng kết nối Postgres bypass RLS.
7. `chat_memory` có index theo `user_id + session_id + created_at`.

## Các điểm Claude Code phải soi kỹ

- Cú pháp `ALTER VIEW ... SET (security_invoker=true)` trên PostgreSQL 17.6.
- Cú pháp signature tạo bằng `pg_get_function_identity_arguments` trong các
  lệnh `REVOKE`, `GRANT` và `ALTER FUNCTION` động.
- Trigger statement-level có chặn đủ UPDATE/DELETE/TRUNCATE trên cả hai bảng.
- Hai hàm `user_has_role` và `user_has_any_role` vẫn callable để RLS không gãy.
- `view_audit_log` hiện hữu vẫn cho admin/QA/auditor đã xác thực đọc.
- n8n `GMP-check` dùng kết nối Postgres nên không bị chặn nhầm khỏi đường INSERT
  hợp lệ; trigger chỉ chặn mutation, không chặn INSERT.
- Rollback khôi phục đúng trạng thái cũ và có cảnh báo rõ rằng trạng thái cũ không
  an toàn.

## Truy vấn xác minh read-only sau khi apply

> Chỉ chạy sau khi người dùng đã xác nhận apply migration 015.

```sql
select c.relname, c.reloptions
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in (
    'documents_effective',
    'documents_due_for_review',
    'documents_review_soon'
  );
```

```sql
select p.proname,
       p.proconfig,
       has_function_privilege('anon', p.oid, 'EXECUTE') as anon_execute,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') as auth_execute,
       has_function_privilege('service_role', p.oid, 'EXECUTE') as service_execute
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in (
    'update_document_status',
    'supersede_document',
    'write_audit_log',
    'get_recent_audit_logs',
    'hybrid_search_v3'
  );
```

```sql
select c.relname as table_name,
       t.tgname,
       pg_get_triggerdef(t.oid) as trigger_definition
from pg_trigger t
join pg_class c on c.oid = t.tgrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('audit_log', 'chat_memory')
  and not t.tgisinternal;
```

```sql
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('audit_log', 'chat_memory')
order by tablename, policyname;
```

## Test negative bắt buộc

- `anon` gọi `update_document_status`: phải bị từ chối quyền EXECUTE.
- `anon` gọi `get_recent_audit_logs`: phải bị từ chối quyền EXECUTE.
- `authenticated` trực tiếp INSERT `audit_log`: phải bị từ chối.
- Kết nối backend thử UPDATE/DELETE/TRUNCATE `audit_log`: trigger phải raise
  SQLSTATE `55000`.
- Kết nối backend thử UPDATE/DELETE/TRUNCATE `chat_memory`: trigger phải raise
  SQLSTATE `55000`.
- INSERT hợp lệ từ backend vào hai bảng vẫn phải thành công.

## Trạng thái

- [x] SQL local đã tạo.
- [x] Rollback local đã tạo.
- [ ] Claude Code review.
- [ ] Người dùng xác nhận SQL.
- [ ] Apply lên project `bdttccztjtrcaztjgkot`.
- [ ] Chạy read-only verification.
- [ ] Chạy negative tests có kiểm soát.

