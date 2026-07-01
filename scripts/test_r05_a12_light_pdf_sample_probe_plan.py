#!/usr/bin/env python3
"""Static assertions for R05-A12 light PDF sample probe plan."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A12-light-pdf-sample-probe-plan.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A12-light-pdf-sample-probe-plan-manifest.json"
GATE_REPORT = ROOT / "work/r05_light_pdf_sample_gate_report.json"
OAUTH_BLOCKER = ROOT / "work/r05_a12_n8n_mcp_oauth_blocker.json"
LIVE_REPORT = ROOT / "work/r05_a12_light_pdf_probe_live_report.json"


class R05A12LightPdfSampleProbePlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.gate_report = json.loads(GATE_REPORT.read_text(encoding="utf-8"))
        cls.oauth_blocker = json.loads(OAUTH_BLOCKER.read_text(encoding="utf-8"))
        cls.live_report = json.loads(LIVE_REPORT.read_text(encoding="utf-8"))

    def test_progress_has_r05_a26_done_and_r05_a27_as_only_active_action(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)
        r05_a12_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A12 |"))
        self.assertIn("| `DONE_SAMPLE_PROBE_NOT_CLOSURE` |", r05_a12_line)
        r05_a13_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A13 |"))
        self.assertIn("| `HOLD_INPUT_REQUIRED` |", r05_a13_line)
        r05_a17_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A17 |"))
        self.assertIn("| `DONE_FAIL_CLOSED_NO_AUTHORITATIVE_CORPUS` |", r05_a17_line)
        r05_a18_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A18 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a18_line)
        r05_a19_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A19 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a19_line)
        r05_a20_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A20 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a20_line)
        r05_a21_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A21 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a21_line)
        r05_a22_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A22 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a22_line)
        r05_a23_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A23 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a23_line)
        r05_a24_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A24 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a24_line)
        r05_a25_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A25 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a25_line)
        r05_a26_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A26 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a26_line)
        r05_a27_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A27 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a27_line)
        r05_a28_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A28 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a28_line)
        r05_a29_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A29 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a29_line)
        r05_a30_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A30 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a30_line)
        r05_a31_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A31 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a31_line)
        r05_a32_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A32 |"))
        self.assertIn("| `DONE` |", r05_a32_line)
        r05_a33_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A33 |"))
        self.assertIn("| `DONE` |", r05_a33_line)
        r05_a34_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A34 |"))
        self.assertIn("| `PARTIAL_LIVE_VERIFIED` |", r05_a34_line)
        r05_a36_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A36 |"))
        self.assertIn("| `DONE` |", r05_a36_line)
        r05_a37_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A37 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a37_line)
        r05_a38_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A38 |"))
        self.assertIn("| `DONE` |", r05_a38_line)
        r05_a39_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A39 |"))
        self.assertIn("| `DONE` |", r05_a39_line)
        r05_a40_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A40 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a40_line)
        r05_a41_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A41 |"))
        self.assertIn("| `DONE` |", r05_a41_line)
        p0_final_line = next(line for line in self.progress.splitlines() if line.startswith("| P0-FINAL-CHECK |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", p0_final_line)
        self.assertIn("FINAL_CHECK_PASS", p0_final_line)
        self.assertIn("PASS_WITH_CAVEAT", p0_final_line)
        active_rows = [
            line
            for line in self.progress.splitlines()
            if line.startswith("| R") and any(status in line for status in [
                "`READY`",
                "`IN_PROGRESS`",
                "`LOCAL_TESTED`",
                "`READY_FOR_APPROVAL`",
                "`USER_APPROVED`",
                "`APPLIED`",
                "`LIVE_VERIFIED`",
                "`FINAL_CHECK`",
            ])
        ]
        self.assertEqual(len(active_rows), 1)
        self.assertTrue(active_rows[0].startswith("| R08-A02 |"))
        self.assertIn("| `IN_PROGRESS` |", active_rows[0])

    def test_sample_gate_is_ready_but_not_authoritative(self) -> None:
        self.assertTrue(self.gate_report["ok"])
        self.assertEqual(self.gate_report["decision"], "READY_FOR_APPROVAL")
        self.assertEqual(self.gate_report["row_count"], 12)
        self.assertEqual(self.gate_report["execution_controls"]["authoritative_closure_claim"], "DENY")
        self.assertEqual(self.gate_report["execution_controls"]["supabase_writes"], "DENY")
        self.assertEqual(self.gate_report["remote_operations"]["n8n"], [])
        self.assertIn("cannot close `BLK-003/004`", self.checkpoint)

    def test_manifest_records_consumed_live_probe_and_required_future_approvals(self) -> None:
        self.assertEqual(self.manifest["rhythm"], "R05-A12")
        self.assertEqual(self.manifest["decision"], "DONE_SAMPLE_PROBE_NOT_CLOSURE")
        self.assertEqual(self.manifest["supabase"]["operations"], [])
        self.assertIn("create_workflow_from_code", self.manifest["n8n"]["operations"])
        self.assertIn("update_workflow:updateNodeParameters(Build Probe Evidence)", self.manifest["n8n"]["operations"])
        self.assertIn("execute_workflow:manual:webhook:12", self.manifest["n8n"]["operations"])
        self.assertTrue(all(approval["consumed"] for approval in self.manifest["approvalsReceived"]))
        self.assertIn("R05-A12 controlled n8n create/update/manual execute for sample probe", self.manifest["approvalsConsumed"])
        self.assertEqual(self.manifest["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-004"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-006"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-007"], "OPEN")

    def test_live_report_records_twelve_successful_non_authoritative_executions(self) -> None:
        self.assertEqual(self.live_report["status"], "DONE_SAMPLE_PROBE_NOT_CLOSURE")
        self.assertEqual(self.live_report["authoritative_corpus_closure"], "DENY")
        self.assertEqual(self.live_report["workflow"]["id"], "XCpn2cKERhsidur8")
        self.assertFalse(self.live_report["workflow"]["active"])
        self.assertIsNone(self.live_report["workflow"]["active_version_id"])
        self.assertFalse(self.live_report["workflow"]["is_archived"])
        self.assertEqual(self.live_report["summary"]["post_update_execution_count"], 12)
        self.assertEqual(self.live_report["summary"]["success_count"], 12)
        self.assertEqual(self.live_report["summary"]["byte_count_match_count"], 12)
        self.assertEqual(self.live_report["summary"]["total_downloaded_byte_count"], 5456352)
        self.assertEqual(self.live_report["summary"]["total_page_count"], 305)
        self.assertEqual(self.live_report["summary"]["text_layer_success_count"], 0)
        self.assertEqual(len(self.live_report["executions"]), 12)
        self.assertTrue(all(row["byte_count_matches_expected"] for row in self.live_report["executions"]))
        self.assertTrue(all(row["parse_status"] == "no_text_layer_or_empty_extract" for row in self.live_report["executions"]))
        self.assertTrue(all(len(row["sha256"]) == 64 for row in self.live_report["executions"]))

    def test_oauth_blocker_is_historical_and_resolved_by_live_report(self) -> None:
        self.assertTrue(self.oauth_blocker["approval_received"])
        self.assertFalse(self.oauth_blocker["approval_consumed"])
        self.assertEqual(self.oauth_blocker["blocked_by"], "n8n MCP OAuth authorization required")
        self.assertFalse(self.oauth_blocker["impact"]["workflow_created"])
        self.assertFalse(self.oauth_blocker["impact"]["workflow_executed"])
        self.assertEqual(self.oauth_blocker["impact"]["supabase_operations"], [])
        self.assertEqual(self.oauth_blocker["impact"]["n8n_operations"], [])
        self.assertEqual(self.manifest["historicalToolBlocker"]["status"], "RESOLVED_BY_MCP_BEARER_TOKEN")


if __name__ == "__main__":
    unittest.main()
