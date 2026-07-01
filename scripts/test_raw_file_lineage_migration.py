#!/usr/bin/env python3
"""Static tests cho CRAVE-026 raw-file lineage."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "supabase/migrations/20260629184000_026_raw_file_lineage.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260629184000_026_raw_file_lineage_down.sql"
CONTRACT = ROOT / "docs/database/raw-file-lineage-contract.md"
CATALOG_TEST = ROOT / "supabase/tests/026_raw_file_lineage_test.sql"


class RawFileLineageMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.contract = CONTRACT.read_text(encoding="utf-8")
        cls.catalog_test = CATALOG_TEST.read_text(encoding="utf-8")

    def test_transaction_and_artifacts(self):
        self.assertTrue(CATALOG_TEST.is_file())
        self.assertRegex(self.forward.lower(), r"(?s)\bbegin;.*\bcommit;\s*$")
        self.assertRegex(self.rollback.lower(), r"(?s)\bbegin;.*\bcommit;\s*$")

    def test_table_idempotency_rls_and_grants(self):
        self.assertIn("create table if not exists public.raw_files", self.forward)
        self.assertIn("alter table public.raw_files enable row level security", self.forward)
        self.assertIn("revoke all on public.raw_files from public, anon", self.forward)
        self.assertIn("to authenticated", self.forward)
        self.assertIn("obj_description(to_regclass('public.raw_files')", self.forward)
        self.assertNotIn("obj_description('public.raw_files'::regclass", self.forward)

    def test_verified_state_requires_real_hash(self):
        for needle in (
            "raw_files_sha256_check",
            "raw_files_verified_check",
            "hash_status = 'verified'",
            "binary_sha256 is not null",
            "verified_at is not null",
        ):
            self.assertIn(needle, self.forward)

    def test_legacy_is_never_marked_verified(self):
        self.assertIn("'legacy_missing'", self.forward)
        self.assertIn("'legacy_unverified'", self.forward)
        legacy_blocks = re.findall(
            r"insert into public\.raw_files[\s\S]*?(?:on conflict|do \$reconcile\$)",
            self.forward,
            re.IGNORECASE,
        )
        self.assertGreaterEqual(len(legacy_blocks), 2)
        self.assertTrue(all("'verified'" not in block for block in legacy_blocks))

    def test_drive_id_is_unique_and_reconciled(self):
        self.assertIn("raw_files_drive_file_key unique (drive_file_id)", self.forward)
        self.assertIn("on conflict (drive_file_id) do update", self.forward)
        self.assertIn("missing_gdrive", self.forward)
        self.assertIn("missing_sync", self.forward)

    def test_no_binary_or_fabricated_document_link(self):
        self.assertNotRegex(self.forward, re.compile(r"\bbytea\b", re.IGNORECASE))
        self.assertNotIn("update public.documents", self.forward.lower())
        self.assertIn("không lưu binary", self.contract)
        self.assertIn("0 file hash", self.contract)

    def test_rollback_refuses_evidence_loss(self):
        self.assertIn("unsafe_rows > 0", self.rollback)
        self.assertIn("rollback refused", self.rollback)
        self.assertIn("binary_sha256 is not null", self.rollback)
        self.assertIn("source_registry_id is not null", self.rollback)

    def test_catalog_test_checks_rls_hash_and_legacy_reconciliation(self):
        for needle in (
            "relrowsecurity",
            "has_table_privilege('anon'",
            "raw_files_sha256_check",
            "legacy_drive_sync_log_ids",
            "false_verified",
        ):
            self.assertIn(needle, self.catalog_test)

    def test_no_audit_mutation(self):
        forbidden = re.compile(
            r"\b(update|delete\s+from|truncate)\s+(table\s+)?public\.audit_log\b",
            re.IGNORECASE,
        )
        self.assertIsNone(forbidden.search(self.forward))
        self.assertIsNone(forbidden.search(self.rollback))


if __name__ == "__main__":
    unittest.main()
