from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "supabase/migrations/20260629191000_027_immutable_document_versions.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260629191000_027_immutable_document_versions_down.sql"
CATALOG_TEST = ROOT / "supabase/tests/027_immutable_document_versions_test.sql"


class DocumentVersionsMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.catalog_test = CATALOG_TEST.read_text(encoding="utf-8")

    def test_marker_and_required_objects(self):
        self.assertIn("20260629191000_027_immutable_document_versions", self.forward)
        self.assertIn("create table if not exists public.document_versions", self.forward)
        self.assertIn("add column if not exists current_version_id uuid", self.forward)
        self.assertIn("documents_current_version_id_fkey", self.forward)

    def test_fail_closed_legacy_backfill(self):
        self.assertIn("'legacy_backfill_027'", self.forward)
        self.assertIn("'legacy_missing'", self.forward)
        self.assertIn("'needs_review'", self.forward)
        self.assertRegex(
            self.forward,
            re.compile(
                r"insert into public\.document_versions[\s\S]*?false,[\s\n]+"
                r"'not_ready'",
                re.IGNORECASE,
            ),
        )
        backfill = self.forward.split(
            "insert into public.document_versions (", 1
        )[1].split("on conflict (document_id, version_label) do nothing;", 1)[0]
        self.assertNotIn("d.approved_for_ai_use", backfill)

    def test_approval_gate_requires_full_evidence(self):
        for token in (
            "approval_evidence_status = 'verified'",
            "binary_sha256 is not null",
            "content_sha256 is not null",
            "hash_status = 'verified'",
            "license_status in ('allowed','curated')",
            "parse_status in ('success','partial')",
            "parse_quality_score is not null",
            "approved_by is not null",
            "approved_at is not null",
        ):
            self.assertIn(token, self.forward)

    def test_immutability_and_pointer_guards(self):
        self.assertIn("crave_enforce_document_version_immutability", self.forward)
        self.assertIn("tg_op = 'delete'", self.forward.lower())
        self.assertIn("approved version bất biến", self.forward)
        self.assertIn("crave_validate_current_document_version", self.forward)
        self.assertIn("version_document_id <> new.id", self.forward)
        self.assertIn("version_superseded_by is not null", self.forward)
        self.assertIn("phải chuyển current_version_id", self.forward)

    def test_ingest_requires_verified_raw_file(self):
        for token in (
            "new.record_origin = 'ingest'",
            "linked_status <> 'verified'",
            "linked_hash_status <> 'verified'",
            "new.binary_sha256 is distinct from linked_binary_sha256",
        ):
            self.assertIn(token, self.forward)

    def test_rls_and_acl_are_restricted(self):
        self.assertIn("alter table public.document_versions enable row level security", self.forward)
        self.assertIn("for select to authenticated", self.forward)
        self.assertIn("revoke all on public.document_versions from public, anon", self.forward)
        self.assertIn("grant select, insert, update on public.document_versions to authenticated", self.forward)
        self.assertNotIn("grant delete", self.forward.lower())

    def test_reconciliation_is_not_hard_coded_to_twelve(self):
        self.assertIn("missing_legacy", self.forward)
        self.assertIn("bad_pointer", self.forward)
        self.assertIn("false_evidence", self.forward)
        self.assertNotRegex(self.forward, re.compile(r"document_count\s*<>\s*12", re.I))

    def test_rollback_refuses_evidence_or_consumers(self):
        self.assertIn("unexpected_rows", self.rollback)
        self.assertIn("unsafe_rows", self.rollback)
        self.assertIn("consumer_fks", self.rollback)
        self.assertIn("rollback từ chối", self.rollback)
        self.assertIn("drop constraint if exists documents_current_version_id_fkey", self.rollback)

    def test_catalog_test_checks_coverage_and_no_false_evidence(self):
        for token in (
            "document_count <> version_count",
            "missing_pointer <> 0",
            "bad_pointer <> 0",
            "false_legacy_evidence <> 0",
            "has_table_privilege('anon','public.document_versions','SELECT')",
        ):
            self.assertIn(token, self.catalog_test)


if __name__ == "__main__":
    unittest.main()
