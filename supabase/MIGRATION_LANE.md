# Supabase CLI deploy lane

Thư mục này là deploy lane cho Supabase CLI. Từ R01-A05R trở đi, chỉ dùng file
timestamped theo format:

```text
<timestamp>_<name>.sql
```

## Quy ước

- Các file timestamped `20260627...` đến `20260629095000...` là historical mirror
  của live migration history đã được đọc từ project `bdttccztjtrcaztjgkot`.
- Các artifact numeric gốc được archive tại
  `supabase/legacy-migrations/numeric-source/`.
- Migration pending mới phải được thêm bằng timestamp lớn hơn latest live
  version và phải PASS:

```bash
supabase db push --linked --dry-run
```

- Chỉ apply bằng:

```bash
supabase db push --linked
```

sau `CODEX SELF-REVIEW`, exact dry-run/change set và approval riêng. Claude Code
không tham dự hoạt động CRAVE hiện hành.

Không đặt file numeric như `024_*.sql`, README hoặc file không đúng pattern vào
`supabase/migrations/`, vì CLI sẽ cảnh báo hoặc hiểu đó là pending migration riêng
và có thể apply sai.

## Historical drift and rollback governance

- `docs/governance/s1-migration-governance-adr.md` closes `BLK-008` by treating
  `021d_eval_score_columns_fix` as a manual-recovery-only exception. Do not add
  or run an automatic downcast rollback from `numeric(5,2)` to `numeric(5,4)`.
- The same ADR closes `BLK-009` by accepting 016/021c history drift through
  `docs/database/live-migration-ledger.md`. Do not run `supabase migration
  repair` for 016/021c without a future separate ADR, exact mapping, dry-run,
  backup/PITR readiness and explicit approval.
