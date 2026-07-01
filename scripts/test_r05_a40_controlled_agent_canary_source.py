#!/usr/bin/env python3
"""Static regression for R05-A40 controlled agent canary source package."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "work/r05_a40_controlled_agent_canary_workflow.js"
LIFECYCLE = ROOT / "work/r05_a40_controlled_agent_canary_lifecycle.sql"
DATASET = ROOT / "eval/datasets/r05_a40_agent_canary_u10_u15.jsonl"
REPORT = ROOT / "work/r05_a40_controlled_agent_canary_report.json"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A40-controlled-agent-canary-source-manifest.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A40-controlled-agent-canary-source.md"
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"


class R05A40ControlledAgentCanarySourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.lifecycle = LIFECYCLE.read_text(encoding="utf-8")
        cls.dataset_rows = [
            json.loads(line)
            for line in DATASET.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")
        cls.workflow_lower = cls.workflow.lower()
        cls.lifecycle_lower = cls.lifecycle.lower()

    def test_workflow_source_is_syntax_valid_and_source_only(self) -> None:
        subprocess.run(["node", "--check", str(WORKFLOW)], cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertIn("TKTL R05-A40 Controlled Agent Canary", self.workflow)
        self.assertEqual(self.report["workflowSource"]["sourceOnly"], True)
        self.assertEqual(self.report["workflowSource"]["n8nCreated"], False)
        self.assertEqual(self.report["workflowSource"]["n8nExecuted"], False)
        self.assertEqual(self.report["workflowSource"]["n8nPublished"], False)
        self.assertEqual(self.manifest["sourceOnlyBoundary"]["n8nCreateUpdateExecutePublishArchive"], False)

    def test_credential_and_node_policy_stays_allowlisted(self) -> None:
        self.assertIn("newCredential('GMP-check')", self.workflow)
        self.assertIn("newCredential('OpenAl')", self.workflow)
        self.assertNotIn("OpenAL", self.workflow)
        self.assertNotIn("googleOAuth2Api", self.workflow)
        self.assertNotIn("postgresTool", self.workflow)
        self.assertNotIn("community", self.workflow_lower)
        self.assertNotIn("crypto", self.workflow_lower)
        self.assertNotIn("variables.", self.workflow_lower)

    def test_user_jwt_retrieval_boundary_is_not_owner_postgres_search(self) -> None:
        self.assertIn("GET", self.workflow)
        self.assertIn("/auth/v1/user", self.workflow)
        self.assertIn("onError: 'continueErrorOutput'", self.workflow)
        self.assertIn("/rest/v1/rpc/hybrid_search_v3", self.workflow)
        self.assertIn("User JWT Hybrid Search", self.workflow)
        self.assertIn("Authorization", self.workflow)
        self.assertIn("__REDACTED_SUPABASE_ANON_KEY__", self.workflow)
        self.assertIn("p_user_id", self.workflow)
        self.assertIn("p_match_count: 3", self.workflow)

    def test_evidence_sql_persists_all_required_a38_a39_relations(self) -> None:
        required_relations = [
            "public.agent_sessions",
            "public.ai_queries",
            "public.retrieval_log",
            "public.retrieval_candidates",
            "public.ai_query_sources",
            "public.tool_call_log",
            "public.system_health_metrics",
            "public.eval_runs",
            "public.eval_results",
            "public.eval_failures",
        ]
        for relation in required_relations:
            self.assertIn(relation, self.workflow)
        self.assertIn("chunk.document_version_id", self.workflow)
        self.assertIn("retrieval_candidate_id", self.workflow)
        self.assertIn("crave_evaluate_eval_v2_release_gate_v1", self.workflow)
        self.assertIn("crave_evaluate_system_health_gate_v1", self.workflow)
        self.assertIn("eval_contract_version", self.workflow)
        self.assertIn("'v2'", self.workflow)
        self.assertIn('"    run_id, question_id, expected_doc', self.workflow)
        self.assertNotIn('"    eval_run_id, question_id, expected_doc', self.workflow)
        for case_id in ("U10-001", "U11-001", "U13-001", "U14-001", "U15-001"):
            self.assertIn(case_id, self.workflow)
        self.assertIn("NULL::uuid", self.workflow)
        self.assertIn("AS gate(case_id, gate_name)", self.workflow)

    def test_lifecycle_plan_requires_retained_identity_and_distinct_qa_approval(self) -> None:
        self.assertIn("NOT FOR APPLY in A40", self.lifecycle)
        self.assertIn(":actor_user_id", self.lifecycle)
        self.assertIn(":qa_created_by", self.lifecycle)
        self.assertIn(":qa_approved_by", self.lifecycle)
        self.assertIn("BLOCK_TWO_PERSON_APPROVAL_REQUIRED", self.lifecycle)
        self.assertIn("hard-delete", self.lifecycle)
        self.assertIn("rollback;", self.lifecycle_lower)
        for forbidden in (
            "delete from public.audit_log",
            "update public.audit_log",
            "truncate public.audit_log",
            "drop table public.audit_log",
        ):
            self.assertNotIn(forbidden, self.lifecycle_lower)

    def test_dataset_fixture_covers_u10_to_u15_without_sensitive_data(self) -> None:
        self.assertEqual(len(self.dataset_rows), 5)
        self.assertEqual({row["gate"] for row in self.dataset_rows}, {"U10", "U11", "U13", "U14", "U15"})
        self.assertEqual(len({row["question_id"] for row in self.dataset_rows}), 5)
        self.assertTrue(all(row["contains_sensitive_data"] is False for row in self.dataset_rows))
        self.assertTrue(all(row["synthetic_only"] is True for row in self.dataset_rows))

    def test_report_manifest_and_checkpoint_keep_blk007_open(self) -> None:
        self.assertEqual(self.report["blockerDisposition"]["BLK-006"], "CLOSED")
        self.assertTrue(self.report["blockerDisposition"]["BLK-007"].startswith("OPEN_"))
        self.assertEqual(self.manifest["blockers"]["BLK-007"], "OPEN")
        self.assertIn("BLK-007 vẫn `OPEN`", self.checkpoint)
        self.assertEqual(self.report["remoteOperations"], {"supabase": [], "supabaseWrites": [], "n8n": [], "drive": [], "git": []})

    def test_progress_tracks_a40_handoff_to_a41_and_blk007_without_final_check(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)
        a40_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A40 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", a40_line)
        a41_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A41 |"))
        self.assertIn("| `DONE` |", a41_line)
        p0_final_line = next(line for line in self.progress.splitlines() if line.startswith("| P0-FINAL-CHECK |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", p0_final_line)
        self.assertIn("FINAL_CHECK_PASS", p0_final_line)
        self.assertIn("PASS_WITH_CAVEAT", p0_final_line)
        blk007_progress = next(line for line in self.progress.splitlines() if line.startswith("| BLK-007 |"))
        blk007_tracker = next(line for line in self.blockers.splitlines() if line.startswith("| BLK-007 |"))
        self.assertIn("| `CLOSED` |", blk007_progress)
        self.assertTrue(blk007_tracker.rstrip().endswith("| CLOSED |"))
        expected_governance_statuses = {
            "BLK-008": "CLOSED",
            "BLK-009": "CLOSED",
            "BLK-010": "CLOSED",
        }
        for blocker_id, expected_status in expected_governance_statuses.items():
            line = next(line for line in self.blockers.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertTrue(line.rstrip().endswith(f"| {expected_status} |"), line)

    def test_manifest_hashes_match_artifacts_after_finalization(self) -> None:
        if self.manifest["decision"] == "PENDING_LOCAL_TESTS":
            self.skipTest("manifest hashes are finalized after local verification")
        mutable_artifacts = {
            "scripts/test_r05_a40_controlled_agent_canary_source.py",
        }
        for artifact in self.manifest["artifacts"]:
            path = ROOT / artifact["path"]
            if artifact["path"] in mutable_artifacts:
                self.assertTrue(path.exists(), artifact["path"])
                continue
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
