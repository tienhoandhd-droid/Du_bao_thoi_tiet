#!/usr/bin/env python3
"""Static safety regression for R05-A39 / CRAVE-030C."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260630221500_030c_eval_v2_health_gate.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260630221500_030c_eval_v2_health_gate_down.sql"
PREFLIGHT = ROOT / "work/r05_a39_eval_v2_health_preflight_readonly.sql"
VERIFY = ROOT / "work/r05_a39_030c_verify_readonly.sql"
CATALOG = ROOT / "supabase/tests/030c_eval_v2_health_gate_catalog_test.sql"
FIXTURE = ROOT / "eval/datasets/r05_a39_eval_v2_failure_fixture.jsonl"
REPORT = ROOT / "work/r05_a39_030c_eval_v2_health_gate_report.json"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A39-030c-eval-v2-health-gate-manifest.json"
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"


class R05A39030CEvalV2HealthGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.migration = MIGRATION.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.preflight = PREFLIGHT.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.catalog = CATALOG.read_text(encoding="utf-8")
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.fixture_rows = [
            json.loads(line)
            for line in FIXTURE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.migration_lower = cls.migration.lower()
        cls.rollback_lower = cls.rollback.lower()
        cls.preflight_lower = cls.preflight.lower()
        cls.verify_lower = cls.verify.lower()
        cls.catalog_lower = cls.catalog.lower()

    def test_forward_migration_is_transactional_and_never_seeds_evidence(self) -> None:
        self.assertTrue(self.migration_lower.lstrip().startswith("-- crave deploy migration"))
        self.assertIn("begin;", self.migration_lower)
        self.assertTrue(self.migration_lower.rstrip().endswith("commit;"))
        self.assertNotIn("insert into", self.migration_lower)
        for forbidden in (
            "update public.audit_log",
            "delete from public.audit_log",
            "truncate public.audit_log",
            "drop table public.audit_log",
        ):
            self.assertNotIn(forbidden, self.migration_lower)

    def test_sql_dollar_quote_tags_are_balanced(self) -> None:
        for source in (self.migration, self.rollback, self.preflight, self.verify, self.catalog):
            tags = Counter(re.findall(r"\$[A-Za-z_][A-Za-z0-9_]*\$", source))
            for tag, count in tags.items():
                self.assertEqual(count % 2, 0, f"unbalanced {tag}: {count}")
        self.assertIn("$function$", self.migration)
        self.assertIn("$rollback_guard$", self.rollback)

    def test_new_tables_are_versioned_rls_and_not_auto_approved(self) -> None:
        for table in ("eval_datasets", "eval_failures"):
            self.assertIn(f"create table if not exists public.{table}", self.migration_lower)
            self.assertIn(f"alter table public.{table} enable row level security", self.migration_lower)
        self.assertIn("status in ('draft', 'approved', 'retired')", self.migration_lower)
        self.assertIn("migration never seeds or approves a dataset", self.migration_lower)
        self.assertIn("artifact_sha256 ~ '^[0-9a-f]{64}$'", self.migration_lower)
        self.assertIn("position('..' in artifact_path) = 0", self.migration_lower)
        self.assertIn("approved_by is distinct from created_by", self.migration_lower)

    def test_legacy_eval_rows_remain_v1_and_v2_requires_full_lineage(self) -> None:
        self.assertIn(
            "add column if not exists eval_contract_version text not null default 'v1'",
            self.migration_lower,
        )
        for column in (
            "dataset_id",
            "retrieval_profile_id",
            "workflow_name",
            "workflow_version",
            "git_commit_sha",
            "release_candidate",
            "run_status",
            "started_at",
            "completed_at",
            "parameters",
        ):
            self.assertIn(f"add column if not exists {column}", self.migration_lower)
        self.assertIn("eval_runs_v2_lineage_check", self.migration_lower)
        self.assertIn("git_commit_sha ~ '^[0-9a-f]{40}$'", self.migration_lower)
        self.assertIn("migration không được tự nâng legacy eval_runs thành v2", self.migration_lower)
        self.assertIn("n_questions không khớp approved dataset", self.migration_lower)

    def test_v2_results_have_normalized_permission_version_tool_and_citation_metrics(self) -> None:
        for column in (
            "retrieval_log_id",
            "ai_query_id",
            "permission_leakage_count",
            "stale_version_count",
            "citation_grounding_score",
            "permission_pass",
            "version_freshness_pass",
            "tool_policy_pass",
            "latency_ms",
            "evaluation_summary",
        ):
            self.assertIn(f"add column if not exists {column}", self.migration_lower)
        self.assertIn("eval_results_v2_metric_ranges_check", self.migration_lower)
        self.assertIn("v2 pass không đạt permission/version/tool/citation assertions", self.migration_lower)
        self.assertIn("idx_eval_results_run_question_unique", self.migration_lower)

    def test_server_validators_fail_closed_on_unapproved_or_mismatched_lineage(self) -> None:
        for function in (
            "crave_validate_eval_run_v2_context",
            "crave_validate_eval_result_v2_context",
            "crave_validate_eval_failure_context",
        ):
            self.assertIn(f"function public.{function}()", self.migration_lower)
        self.assertIn("approved/effective dataset", self.migration_lower)
        self.assertIn("approved/effective retrieval profile", self.migration_lower)
        self.assertIn("retrieval/query lineage không khớp", self.migration_lower)
        self.assertIn("failed v2 eval result", self.migration_lower)

    def test_health_gate_is_bounded_stable_security_invoker_and_fail_closed(self) -> None:
        self.assertIn(
            "function public.crave_evaluate_system_health_gate_v1(",
            self.migration_lower,
        )
        self.assertIn("stable\nsecurity invoker", self.migration_lower)
        self.assertIn("set search_path = public, pg_temp", self.migration_lower)
        self.assertIn("cardinality(required_metrics) > 32", self.migration_lower)
        self.assertIn("interval '1 minute'", self.migration_lower)
        self.assertIn("interval '24 hours'", self.migration_lower)
        self.assertIn("p_freshness is null", self.migration_lower)
        self.assertIn("latest.status <> 'healthy'", self.migration_lower)
        self.assertIn("cardinality(missing_metrics) = 0", self.migration_lower)

    def test_eval_v2_release_gate_requires_complete_zero_failure_evidence(self) -> None:
        self.assertIn(
            "function public.crave_evaluate_eval_v2_release_gate_v1(",
            self.migration_lower,
        )
        self.assertIn("untracked_failed_result_count", self.migration_lower)
        self.assertIn("result_count = run_row.n_questions", self.migration_lower)
        self.assertIn("permission_leakage_total = 0", self.migration_lower)
        self.assertIn("stale_version_total = 0", self.migration_lower)
        self.assertIn("citation_failure_count = 0", self.migration_lower)
        self.assertIn("tool_failure_count = 0", self.migration_lower)

    def test_authenticated_broad_eval_writes_are_removed(self) -> None:
        self.assertIn(
            "revoke insert, update, delete, truncate on table",
            self.migration_lower,
        )
        self.assertIn("from authenticated", self.migration_lower)
        self.assertIn("drop policy if exists eval_runs_insert_authenticated", self.migration_lower)
        self.assertIn("drop policy if exists eval_results_insert_authenticated", self.migration_lower)
        self.assertIn("drop policy if exists eval_runs_select_authenticated", self.migration_lower)
        self.assertIn("drop policy if exists eval_results_select_authenticated", self.migration_lower)
        self.assertIn("eval_runs_read_auditor", self.migration_lower)
        self.assertIn("eval_results_read_auditor", self.migration_lower)
        self.assertIn(
            "revoke execute on function public.run_fts_eval_v1(integer, text, text)",
            self.migration_lower,
        )
        self.assertIn("from authenticated", self.migration_lower)
        self.assertIn("grant select, insert on table", self.migration_lower)
        self.assertIn("to service_role", self.migration_lower)

    def test_eval_evidence_relations_are_append_only(self) -> None:
        for table in ("eval_datasets", "eval_runs", "eval_results", "eval_failures"):
            self.assertIn(f"'{table}'", self.migration_lower)
        self.assertIn("trigger_name := target_table || '_append_only_guard'", self.migration_lower)
        self.assertIn("before update or delete or truncate", self.migration_lower)
        self.assertIn("crave_block_append_only_mutation()", self.migration_lower)

    def test_rollback_refuses_to_destroy_v2_evidence_and_restores_legacy_insert_contract(self) -> None:
        self.assertIn("eval_datasets có % rows", self.rollback_lower)
        self.assertIn("eval_failures có % rows", self.rollback_lower)
        self.assertIn("eval_runs đã có v2 evidence", self.rollback_lower)
        self.assertIn("eval_results đã có v2 evidence", self.rollback_lower)
        self.assertIn("grant insert on table public.eval_runs, public.eval_results", self.rollback_lower)
        self.assertIn(
            "grant execute on function public.run_fts_eval_v1(integer, text, text)",
            self.rollback_lower,
        )
        self.assertIn("eval_runs_insert_authenticated", self.rollback_lower)
        self.assertIn("eval_results_insert_authenticated", self.rollback_lower)
        self.assertIn("eval_runs_select_authenticated", self.rollback_lower)
        self.assertIn("eval_results_select_authenticated", self.rollback_lower)
        self.assertTrue(self.rollback_lower.rstrip().endswith("commit;"))

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
        self.assertIn("ready_for_exact_030c_apply_approval", self.preflight_lower)
        self.assertIn("pass_030c_eval_v2_health_gate", self.verify_lower)

    def test_catalog_test_is_assertion_only(self) -> None:
        for forbidden in ("insert into", "update ", "delete from", "truncate "):
            self.assertNotIn(forbidden, self.catalog_lower)
        self.assertIn("authenticated có broad eval evidence write path", self.catalog_lower)
        self.assertIn("pass_030c_eval_v2_health_gate_catalog", self.catalog_lower)

    def test_failure_fixture_covers_u10_u11_u13_u14_u15_without_sensitive_data(self) -> None:
        self.assertEqual(len(self.fixture_rows), 5)
        self.assertEqual({row["gate"] for row in self.fixture_rows}, {"U10", "U11", "U13", "U14", "U15"})
        self.assertEqual(len({row["fixture_id"] for row in self.fixture_rows}), 5)
        self.assertTrue(all(row["contract_version"] == "v2" for row in self.fixture_rows))
        self.assertTrue(all(row["contains_sensitive_data"] is False for row in self.fixture_rows))
        self.assertEqual(
            {row["failure_type"] for row in self.fixture_rows},
            {
                "permission_leakage",
                "citation_grounding",
                "retrieval_miss",
                "version_freshness",
                "health_assertion",
            },
        )

    def test_canonical_state_preserves_a39_done_after_a42_closure(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        a39_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A39 |"))
        self.assertIn("| `DONE` |", a39_line)
        a40_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A40 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", a40_line)
        a41_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A41 |"))
        p0_final_line = next(line for line in self.progress.splitlines() if line.startswith("| P0-FINAL-CHECK |"))
        self.assertIn("| `DONE` |", a41_line)
        self.assertIn("| `DONE_SOURCE_ONLY` |", p0_final_line)
        self.assertIn("FINAL_CHECK_PASS", p0_final_line)
        blk007_progress = next(line for line in self.progress.splitlines() if line.startswith("| BLK-007 |"))
        blk007_tracker = next(line for line in self.blockers.splitlines() if line.startswith("| BLK-007 |"))
        self.assertIn("| `CLOSED` |", blk007_progress)
        self.assertTrue(blk007_tracker.rstrip().endswith("| CLOSED |"))

    def test_report_manifest_and_artifact_hashes_record_live_verified_boundary(self) -> None:
        self.assertEqual(self.report["decision"], "PASS_030C_EVAL_V2_HEALTH_GATE")
        self.assertEqual(self.report["status"], "DONE_LIVE_VERIFIED")
        self.assertTrue(self.manifest["liveEvidence"]["applied"])
        self.assertEqual(self.manifest["decision"], "PASS_030C_EVAL_V2_HEALTH_GATE")
        self.assertIn(
            "applied exactly 20260630221500_030c_eval_v2_health_gate.sql",
            self.manifest["remoteOperations"]["supabaseWrites"],
        )
        self.assertEqual(self.manifest["remoteOperations"]["n8n"], [])
        self.assertEqual(self.manifest["blockers"]["BLK-007"], "OPEN")
        mutable_artifacts = {
            "scripts/test_r05_a39_030c_eval_v2_health_gate.py",
        }
        for artifact in self.manifest["artifacts"]:
            path = ROOT / artifact["path"]
            if artifact["path"] in mutable_artifacts:
                self.assertTrue(path.exists(), artifact["path"])
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
