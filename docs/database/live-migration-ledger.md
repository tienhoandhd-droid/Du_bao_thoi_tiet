# CRAVE live migration ledger

Ledger này là bản đồ canonical giữa migration history live của Supabase và
semantic source artifact trong repo. Mục tiêu là tránh lặp lại drift giữa tên
file local dạng `013_...` và version live dạng timestamp của Supabase CLI.

## Nguyên tắc từ R01-A05R trở đi

- `supabase/migrations/` chỉ chứa migration deployable theo format Supabase CLI:
  `<timestamp>_<name>.sql`.
- SQL numeric/legacy được lưu làm source artifact lịch sử trong
  `supabase/legacy-migrations/numeric-source/`.
- Rollback numeric/legacy được lưu trong
  `supabase/legacy-rollbacks/numeric-source/`.
- Migration chính phải apply bằng `supabase db push --linked` sau
  `supabase db push --linked --dry-run`.
- Không dùng `supabase db query --linked --file` cho migration chính, trừ
  emergency có approval riêng và ghi rõ caveat trong progress/checkpoint.
- Mọi migration live cần có rollback tương ứng, test/catalog check và progress
  evidence.

## Live history đã đọc từ project `bdttccztjtrcaztjgkot`

Nguồn evidence:

- Command: `supabase db query --linked "select version, name from supabase_migrations.schema_migrations order by version;"`
- Thời điểm đọc: 2026-06-29 16:04 +07.
- Loại evidence: read-only; không SQL write/apply.

| Live version | Live name | Semantic/source artifact | Trạng thái |
|---|---|---|---|
| `20260627012519` | `013_citation_grounding` | `supabase/legacy-migrations/numeric-source/013_citation_grounding.sql` | Live history exists |
| `20260627024207` | `014_chat_memory` | `supabase/legacy-migrations/numeric-source/014_chat_memory.sql` | Live history exists |
| `20260627110302` | `015_platform_security_hardening` | `supabase/legacy-migrations/numeric-source/015_platform_security_hardening.sql` | Live history exists |
| `20260627200153` | `017_equipment_glossary` | `supabase/legacy-migrations/numeric-source/017_equipment_glossary.sql` | Live history exists |
| `20260627204445` | `018_seed_validation_data` | `supabase/legacy-migrations/numeric-source/018_seed_validation_data.sql` | Live history exists |
| `20260628013552` | `019_drive_sync_log` | `supabase/legacy-migrations/numeric-source/019_drive_sync_log.sql` | Live history exists |
| `20260628070328` | `020_validation_sessions` | `supabase/legacy-migrations/numeric-source/020_validation_sessions.sql` | Live history exists |
| `20260628112355` | `021_eval_harness` | `supabase/legacy-migrations/numeric-source/021_eval_harness.sql` | Live history exists |
| `20260628113034` | `021b_eval_function_v2` | `supabase/legacy-migrations/numeric-source/021b_eval_function_v2.sql` | Live history exists |
| `20260628113529` | `021c_eval_function_v3_or_tsquery` | `supabase/legacy-migrations/numeric-source/021c_eval_function_v3.sql` | Live history exists; live name differs slightly from local legacy filename |
| `20260628113613` | `021d_eval_score_columns_fix` | `supabase/legacy-migrations/numeric-source/021d_eval_score_columns_fix.sql` | Live history exists |
| `20260628125753` | `022_fix_eval_rank_order` | `supabase/legacy-migrations/numeric-source/022_fix_eval_rank_order.sql` | Live history exists |
| `20260629095000` | `023_harden_run_fts_eval_v1` | `supabase/legacy-migrations/numeric-source/023_harden_run_fts_eval_v1.sql` | Latest verified live migration before R01-A05 |

## Pending deploy lane

| Planned version | Name | Semantic/source ID | Source artifact | Rollback artifact | Status |
|---|---|---|---|---|---|
| `20260629110000` | `r01_search_documents_v1` | `CRAVE-024 / R01-A02 / R01-A05R` | `supabase/migrations/20260629110000_r01_search_documents_v1.sql` | `supabase/rollbacks/20260629110000_r01_search_documents_v1_down.sql` | Pending dry-run/review/apply |

## Accepted migration governance notes

- `016_eval_harness.sql` exists as legacy source but no corresponding live
  `016_*` row was present in the read-only history output. This drift is
  accepted by `docs/governance/s1-migration-governance-adr.md` for `BLK-009`
  and must not be silently repaired.
- `021d_eval_score_columns_fix` widens eval percentage columns from
  `numeric(5,4)` to `numeric(5,2)`. `BLK-008` is closed by the same ADR as a
  manual-recovery-only rollback exception; do not auto-downcast live eval
  evidence to the old precision.
- Legacy `_down.sql` files that previously lived under `supabase/migrations/`
  are archived under `supabase/legacy-migrations/numeric-source/` to prevent
  Supabase CLI from treating them as deployable migrations.
- Do not use `supabase migration repair` without a separate ADR, exact mapping,
  backup/PITR readiness, dry-run evidence, approval and Codex final governance
  verification.
