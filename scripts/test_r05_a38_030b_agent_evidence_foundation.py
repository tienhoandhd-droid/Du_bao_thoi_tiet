#!/usr/bin/env python3
"""Static safety regression for R05-A38 CRAVE-030B evidence foundation."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260630213500_030b_agent_evidence_foundation.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260630213500_030b_agent_evidence_foundation_down.sql"
PREFLIGHT = ROOT / "work/r05_a38_030b_preflight_readonly.sql"
VERIFY = ROOT / "work/r05_a38_030b_verify_readonly.sql"
CATALOG_TEST = ROOT / "supabase/tests/030b_agent_evidence_foundation_catalog_test.sql"
REPORT = ROOT / "work/r05_a38_030b_agent_evidence_foundation_report.json"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A38-030b-agent-evidence-foundation-manifest.json"

TARGET_TABLES = (
    "retrieval_profiles",
    "retrieval_log",
    "retrieval_candidates",
    "agent_sessions",
    "tool_call_log",
    "system_health_metrics",
)


class R05A38030BAgentEvidenceFoundationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.migration = MIGRATION.read_text(encoding="utf-8")
        cls.migration_lower = cls.migration.lower()
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.rollback_lower = cls.rollback.lower()
        cls.preflight = PREFLIGHT.read_text(encoding="utf-8")
        cls.preflight_lower = cls.preflight.lower()
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.verify_lower = cls.verify.lower()
        cls.catalog_test = CATALOG_TEST.read_text(encoding="utf-8")
        cls.catalog_test_lower = cls.catalog_test.lower()
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_forward_and_rollback_have_explicit_transactions(self) -> None:
        for source in (self.migration, self.rollback):
            self.assertEqual(len(re.findall(r"(?im)^begin;\s*$", source)), 1)
            self.assertEqual(len(re.findall(r"(?im)^commit;\s*$", source)), 1)
            self.assertEqual(len(re.findall(r"(?im)^rollback;\s*$", source)), 0)

    def test_forward_creates_all_foundation_tables_idempotently_with_markers(self) -> None:
        for table in TARGET_TABLES:
            self.assertIn(f"create table if not exists public.{table}", self.migration_lower)
            self.assertIn(f"comment on table public.{table}", self.migration_lower)
        self.assertGreaterEqual(self.migration.count("CRAVE-030B:"), 20)
        self.assertNotIn("insert into public.retrieval_profiles", self.migration_lower)

    def test_every_new_table_has_rls_and_no_authenticated_write_grant(self) -> None:
        for table in TARGET_TABLES:
            self.assertIn(f"alter table public.{table} enable row level security", self.migration_lower)
        self.assertIn("grant select on table", self.migration_lower)
        self.assertNotRegex(
            self.migration_lower,
            r"grant\s+(?:insert|update|delete|all).*?to\s+authenticated",
        )
        for policy in (
            "retrieval_profiles_read_approved_or_auditor",
            "retrieval_log_read_own_or_auditor",
            "retrieval_candidates_read_own_or_auditor",
            "agent_sessions_read_own_or_auditor",
            "tool_call_log_read_own_or_auditor",
            "system_health_metrics_read_auditor",
        ):
            self.assertIn(policy, self.migration_lower)

    def test_append_only_evidence_guards_cover_required_relations(self) -> None:
        for relation in (
            "retrieval_log",
            "retrieval_candidates",
            "tool_call_log",
            "system_health_metrics",
            "ai_query_sources",
        ):
            self.assertIn(relation, self.migration_lower)
            self.assertIn(f"{relation}_append_only_guard", self.verify_lower)
        self.assertIn("public.crave_block_append_only_mutation()", self.migration_lower)

    def test_citation_contract_is_explicit_and_fail_closed(self) -> None:
        for column in (
            "document_version_id",
            "retrieval_candidate_id",
            "final_score",
            "citation_verified_at",
        ):
            self.assertIn(f"add column if not exists {column}", self.migration_lower)
        self.assertIn("crave_validate_ai_query_source_lineage", self.migration_lower)
        self.assertIn("ai_query_sources_validate_lineage", self.migration_lower)
        self.assertIn("candidate.selected = true", self.migration_lower)
        self.assertIn("candidate_query_id is distinct from new.query_id", self.migration_lower)
        self.assertIn("and retrieval_candidate_id is not null", self.migration_lower)
        self.assertIn("alter column document_version_id set not null", self.migration_lower)
        self.assertIn("ai_query_sources không rỗng", self.migration)

    def test_retrieval_context_and_candidate_lineage_are_server_enforced(self) -> None:
        self.assertIn("crave_validate_retrieval_log_context", self.migration_lower)
        self.assertIn("retrieval_log_validate_context", self.migration_lower)
        self.assertIn("query_user_id is distinct from new.user_id", self.migration_lower)
        self.assertIn("profile_status <> 'approved'", self.migration_lower)
        self.assertIn("crave_validate_retrieval_candidate_lineage", self.migration_lower)
        self.assertIn("retrieval_candidates_validate_lineage", self.migration_lower)
        self.assertIn("chunk_version_id is distinct from new.document_version_id", self.migration_lower)

    def test_audit_log_is_never_mutated_or_dropped(self) -> None:
        combined = "\n".join((self.migration_lower, self.rollback_lower))
        for pattern in (
            r"update\s+public\.audit_log",
            r"delete\s+from\s+public\.audit_log",
            r"truncate\s+(?:table\s+)?public\.audit_log",
            r"drop\s+table(?:\s+if\s+exists)?\s+public\.audit_log",
        ):
            self.assertIsNone(re.search(pattern, combined), pattern)

    def test_rollback_refuses_to_destroy_evidence_and_drops_in_dependency_order(self) -> None:
        for table in TARGET_TABLES:
            self.assertIn(f"'{table}'", self.rollback_lower)
        self.assertIn("rollback từ chối", self.rollback_lower)
        self.assertIn("ai_query_sources đã dùng citation evidence mới", self.rollback_lower)
        positions = [
            self.rollback_lower.index("drop table if exists public.system_health_metrics"),
            self.rollback_lower.index("drop table if exists public.tool_call_log"),
            self.rollback_lower.index("drop table if exists public.agent_sessions"),
            self.rollback_lower.index("drop table if exists public.retrieval_candidates"),
            self.rollback_lower.index("drop table if exists public.retrieval_log"),
            self.rollback_lower.index("drop table if exists public.retrieval_profiles"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_preflight_and_verify_are_read_only(self) -> None:
        for source in (self.preflight_lower, self.verify_lower):
            for forbidden in (
                "insert into",
                "update ",
                "delete from",
                "truncate ",
                "alter table",
                "create table",
                "drop table",
            ):
                self.assertNotIn(forbidden, source)
        self.assertIn("ready_for_exact_030b_apply_approval", self.preflight_lower)
        self.assertIn("pass_030b_agent_evidence_foundation", self.verify_lower)

    def test_catalog_test_is_assertion_only_and_checks_denied_writes(self) -> None:
        for forbidden in ("insert into", "update ", "delete from", "truncate "):
            self.assertNotIn(forbidden, self.catalog_test_lower)
        self.assertIn("authenticated có broad evidence insert", self.catalog_test_lower)
        self.assertIn("pass_030b_agent_evidence_foundation_catalog", self.catalog_test_lower)

    def test_timestamped_migration_is_retained_and_has_matching_rollback(self) -> None:
        migration_names = sorted(path.name for path in (ROOT / "supabase/migrations").glob("*.sql"))
        self.assertIn(MIGRATION.name, migration_names)
        self.assertTrue(all(name > MIGRATION.name for name in migration_names if "_030c_" in name))
        self.assertTrue(ROLLBACK.exists())
        self.assertIn("20260630213500_030b_agent_evidence_foundation", self.migration)
        self.assertIn("20260630213500_030b_agent_evidence_foundation", self.rollback)

    def test_report_and_manifest_record_exact_live_apply_boundary(self) -> None:
        self.assertEqual(self.report["decision"], "PASS_030B_AGENT_EVIDENCE_FOUNDATION")
        self.assertTrue(self.manifest["liveEvidence"]["applied"])
        self.assertEqual(
            self.manifest["liveEvidence"]["appliedMigration"],
            "20260630213500_030b_agent_evidence_foundation.sql",
        )
        self.assertEqual(
            self.manifest["liveEvidence"]["verifyDecision"],
            "PASS_030B_AGENT_EVIDENCE_FOUNDATION",
        )
        self.assertEqual(
            self.manifest["liveEvidence"]["catalogDecision"],
            "PASS_030B_AGENT_EVIDENCE_FOUNDATION_CATALOG",
        )
        self.assertFalse(self.manifest["liveEvidence"]["rollbackExecuted"])
        self.assertEqual(
            self.manifest["remoteOperations"]["supabaseWrites"],
            ["applied exactly 20260630213500_030b_agent_evidence_foundation.sql"],
        )
        self.assertEqual(self.manifest["remoteOperations"]["n8n"], [])
        self.assertEqual(self.manifest["blockers"]["BLK-006"], "CLOSED")
        self.assertEqual(self.manifest["blockers"]["BLK-007"], "OPEN")

    def test_manifest_artifact_hashes_match(self) -> None:
        for artifact in self.manifest["artifacts"]:
            path = ROOT / artifact["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
