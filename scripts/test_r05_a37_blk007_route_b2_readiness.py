#!/usr/bin/env python3
"""Regression for R05-A37 BLK-007 Route B2 fail-closed readiness."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "work/r05_a37_blk007_route_b2_readiness_report.json"
WF12 = ROOT / "n8n/workflows/TKTL-WF-12-qa-assistant-agentic.json"
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"


class R05A37Blk007RouteB2ReadinessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.workflow = json.loads(WF12.read_text(encoding="utf-8"))
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")
        cls.nodes = {node["name"]: node for node in cls.workflow["nodes"]}

    def test_live_readiness_fails_closed_on_missing_evidence_tables(self) -> None:
        self.assertEqual(
            self.report["decision"],
            "ROUTE_B2_CANARY_NOT_READY_EVIDENCE_FOUNDATION_REQUIRED",
        )
        self.assertEqual(
            set(self.report["liveReadOnlyEvidence"]["missingRequiredTables"]),
            {
                "retrieval_profiles",
                "retrieval_log",
                "retrieval_candidates",
                "tool_call_log",
                "agent_sessions",
                "eval_datasets",
                "eval_failures",
                "system_health_metrics",
            },
        )
        self.assertEqual(self.report["blockerDisposition"]["BLK-006"], "CLOSED")
        self.assertTrue(self.report["blockerDisposition"]["BLK-007"].startswith("OPEN_"))

    def test_wf12_has_baseline_controls_but_missing_persisted_agent_evidence(self) -> None:
        credentials = {
            value["name"]
            for node in self.workflow["nodes"]
            for value in (node.get("credentials") or {}).values()
        }
        self.assertEqual(credentials, {"GMP-check", "OpenAl"})
        self.assertEqual(self.nodes["Verify JWT"].get("onError"), "continueErrorOutput")
        self.assertIn("/auth/v1/user", self.nodes["Verify JWT"]["parameters"]["url"])
        self.assertIn("public.hybrid_search_v3", self.nodes["rag_search"]["parameters"]["query"])
        audit_sql = self.nodes["Audit INSERT"]["parameters"]["query"].lower()
        self.assertIn("insert into public.ai_queries", audit_sql)
        self.assertNotIn("insert into public.ai_query_sources", audit_sql)
        self.assertNotIn("tool_call_log", audit_sql)
        self.assertNotIn("retrieval_log", audit_sql)

    def test_selected_route_requires_foundation_before_agent_execution(self) -> None:
        phases = " ".join(self.report["selectedRoute"]["phases"])
        self.assertIn("030b", phases)
        self.assertIn("eval-v2", phases)
        self.assertIn("controlled-agent", phases)
        self.assertIn("exact Supabase apply", phases)
        self.assertIn("Do not execute WF-12/WF-13", " ".join(self.report["stopConditions"]))

    def test_no_n8n_or_supabase_write_was_claimed(self) -> None:
        remote = self.report["remoteOperations"]
        self.assertEqual(remote["supabaseWrites"], [])
        self.assertEqual(remote["n8n"], [])
        self.assertEqual(remote["drive"], [])
        self.assertEqual(remote["git"], [])

    def test_canonical_state_keeps_only_blk007_open(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)
        r05_a37 = next(line for line in self.progress.splitlines() if line.startswith("| R05-A37 |"))
        r05_a38 = next(line for line in self.progress.splitlines() if line.startswith("| R05-A38 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a37)
        self.assertIn("| `DONE` |", r05_a38)
        r05_a39 = next(line for line in self.progress.splitlines() if line.startswith("| R05-A39 |"))
        self.assertIn("| `DONE` |", r05_a39)
        r05_a40 = next(line for line in self.progress.splitlines() if line.startswith("| R05-A40 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a40)
        r05_a41 = next(line for line in self.progress.splitlines() if line.startswith("| R05-A41 |"))
        self.assertIn("| `DONE` |", r05_a41)
        p0_final_line = next(line for line in self.progress.splitlines() if line.startswith("| P0-FINAL-CHECK |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", p0_final_line)
        self.assertIn("FINAL_CHECK_PASS", p0_final_line)
        blk006_progress = next(line for line in self.progress.splitlines() if line.startswith("| BLK-006 |"))
        blk007_progress = next(line for line in self.progress.splitlines() if line.startswith("| BLK-007 |"))
        blk006_tracker = next(line for line in self.blockers.splitlines() if line.startswith("| BLK-006 |"))
        blk007_tracker = next(line for line in self.blockers.splitlines() if line.startswith("| BLK-007 |"))
        self.assertIn("| `CLOSED` |", blk006_progress)
        self.assertIn("| `CLOSED` |", blk007_progress)
        self.assertTrue(blk006_tracker.rstrip().endswith("| CLOSED |"))
        self.assertTrue(blk007_tracker.rstrip().endswith("| CLOSED |"))
        expected_governance_statuses = {
            "BLK-008": "CLOSED",
            "BLK-009": "CLOSED",
            "BLK-010": "CLOSED",
        }
        for blocker_id, expected_status in expected_governance_statuses.items():
            line = next(line for line in self.blockers.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertTrue(line.rstrip().endswith(f"| {expected_status} |"), line)


if __name__ == "__main__":
    unittest.main()
