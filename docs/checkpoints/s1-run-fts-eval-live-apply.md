# S1 live apply evidence — migration 023

**Ngày:** 2026-06-29
**Project:** `bdttccztjtrcaztjgkot`
**Migration:** `023_harden_run_fts_eval_v1`
**Live operation:** applied via `psql` after explicit user confirmation
**Result:** **PASS**

## 1. Approval

User confirmation:

> “Xác nhận apply migration 023 live”

## 2. Applied operations

Transaction committed successfully:

- `ALTER FUNCTION public.run_fts_eval_v1(integer, text, text) SET search_path TO pg_catalog, public, extensions`
- `REVOKE ALL ... FROM public`
- `REVOKE ALL ... FROM anon`
- `GRANT EXECUTE ... TO authenticated`
- `GRANT EXECUTE ... TO service_role`
- Inserted migration record:
  - version: `20260629095000`
  - name: `023_harden_run_fts_eval_v1`

No eval data, audit data, documents, n8n workflow or frontend state was changed.

## 3. Post-apply verification

Read-only verification after commit:

| Attribute | Observed | Expected | Result |
|---|---|---|---|
| Function exists | `public.run_fts_eval_v1(integer,text,text)` | present | PASS |
| `SECURITY DEFINER` | true | true | PASS |
| `search_path` | `pg_catalog, public, extensions` | `pg_catalog, public, extensions` | PASS |
| `anon` execute | false | false | PASS |
| `authenticated` execute | true | true | PASS |
| `service_role` execute | true | true | PASS |
| Migration record | `20260629095000 / 023_harden_run_fts_eval_v1` | present | PASS |

## 4. S1 impact

The specific finding “`run_fts_eval_v1` SECURITY DEFINER missing locked
search_path and executable by anon” is now remediated live.

S1 still remains HOLD because the following blockers are not closed by migration
023:

- rollback `021d` is unsafe with live eval data;
- WF-06 direct SQL/credential boundary remains unresolved;
- Issue #2 governance state is stale/open;
- migration history drift `016`/`021c` still requires change-control explanation.
