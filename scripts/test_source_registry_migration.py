#!/usr/bin/env python3
"""Static regression tests cho CRAVE-025 source/license gate."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "supabase/migrations/20260629182000_025_source_registry_license_gate.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260629182000_025_source_registry_license_gate_down.sql"
CATALOG_TEST = ROOT / "supabase/tests/025_source_registry_license_gate_test.sql"
CONTRACT = ROOT / "docs/database/source-registry-license-contract.md"


class SourceRegistryMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.catalog_test = CATALOG_TEST.read_text(encoding="utf-8")
        cls.contract = CONTRACT.read_text(encoding="utf-8")

    def test_artifacts_and_transaction_boundaries_exist(self):
        for path in (FORWARD, ROLLBACK, CATALOG_TEST, CONTRACT):
            self.assertTrue(path.is_file(), path)
        self.assertRegex(self.forward.lower(), r"(?s)\bbegin;.*\bcommit;\s*$")
        self.assertRegex(self.rollback.lower(), r"(?s)\bbegin;.*\bcommit;\s*$")

    def test_tables_are_idempotent_and_rls_enabled(self):
        self.assertIn("create table if not exists public.source_registry", self.forward)
        self.assertIn("create table if not exists public.license_rules", self.forward)
        self.assertIn("alter table public.source_registry enable row level security", self.forward)
        self.assertIn("alter table public.license_rules enable row level security", self.forward)
        self.assertIn("where schemaname = 'public'", self.forward)
        self.assertIn("obj_description(to_regclass('public.source_registry')", self.forward)
        self.assertNotIn("obj_description('public.source_registry'::regclass", self.forward)

    def test_legacy_import_is_fail_closed_and_reconciled(self):
        self.assertIn("'metadata_only'", self.forward)
        self.assertIn("false,\n  legacy_ids", self.forward)
        self.assertIn("legacy_web_source_ids", self.forward)
        self.assertIn("missing_count > 0", self.forward)
        self.assertNotRegex(
            self.forward,
            re.compile(r"from public\.web_sources[\s\S]{0,800}'allow'", re.IGNORECASE),
        )

    def test_unknown_inactive_and_expired_fail_closed(self):
        self.assertIn("unknown_inactive_or_expired_source", self.forward)
        self.assertIn("'decision', 'deny'", self.forward)
        self.assertIn("'allow_fetch', false", self.forward)
        self.assertIn("s.is_active", self.forward)
        self.assertIn("s.effective_from <= v_at", self.forward)

    def test_resolver_is_typed_invoker_and_locked(self):
        self.assertIn("create or replace function public.resolve_source_policy_v1", self.forward)
        self.assertIn("stable\nsecurity invoker", self.forward.lower())
        self.assertIn("set search_path to pg_catalog, public", self.forward)
        self.assertIn("revoke all on function", self.forward)
        self.assertIn("grant execute on function", self.forward)

    def test_license_rules_are_append_only(self):
        self.assertIn("license_rules_append_only_guard", self.forward)
        self.assertIn("before update or delete or truncate", self.forward)
        self.assertIn("crave_block_append_only_mutation", self.forward)
        self.assertNotIn("grant update", self.forward.split("public.license_rules to authenticated")[0][-100:])

    def test_rollback_refuses_evidence_loss(self):
        self.assertIn("rule_count > 0 or unsafe_sources > 0", self.rollback)
        self.assertIn("rollback refused", self.rollback)
        self.assertIn("CRAVE-025:%", self.rollback)
        self.assertLess(
            self.rollback.index("drop table if exists public.license_rules"),
            self.rollback.index("drop table if exists public.source_registry"),
        )

    def test_no_audit_history_mutation(self):
        forbidden = re.compile(
            r"\b(update|delete\s+from|truncate)\s+(table\s+)?public\.audit_log\b",
            re.IGNORECASE,
        )
        self.assertIsNone(forbidden.search(self.forward))
        self.assertIsNone(forbidden.search(self.rollback))

    def test_catalog_test_covers_security_and_fail_closed(self):
        for needle in (
            "relrowsecurity",
            "license_rules_append_only_guard",
            "SECURITY INVOKER",
            "has_table_privilege('anon'",
            "unknown source không fail closed",
        ):
            self.assertIn(needle, self.catalog_test)

    def test_contract_does_not_claim_legacy_legal_approval(self):
        self.assertIn("không được coi là approval pháp lý", self.contract)
        self.assertIn("metadata_only", self.contract)
        self.assertIn("is_active=false", self.contract)


if __name__ == "__main__":
    unittest.main()
