#!/usr/bin/env python3
"""Static assertions for R05-A10 P0 BLK-004 closure plan."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A10-p0-open-items-blk004-closure-plan.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A10-p0-open-items-blk004-closure-plan-manifest.json"
MAPPING_TEMPLATE = ROOT / "work/r05_a10_authoritative_mapping_required.csv"
WORKFLOW_P_CONTRACT = ROOT / "n8n/workflow-contracts/TKTL-Workflow-P-staging-review.contract.json"


REQUIRED_CODES = {
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
}


class R05A10P0ClosurePlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.contract = json.loads(WORKFLOW_P_CONTRACT.read_text(encoding="utf-8"))
        with MAPPING_TEMPLATE.open(encoding="utf-8", newline="") as handle:
            cls.mapping_rows = list(csv.DictReader(handle))

    def test_progress_preserves_r05_a10_input_blocker_handoff(self) -> None:
        self.assertIn("| R05-A10 |", self.progress)
        r05_a10_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A10 |"))
        self.assertIn("| `DONE_SOURCE_ONLY_INPUT_BLOCKED` |", r05_a10_line)
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

    def test_p0_blockers_are_not_falsely_closed(self) -> None:
        self.assertIn("| BLK-003 | P0 | 12/12 live accepted reference/current-version bindings verified", self.progress)
        self.assertIn("A32 live apply/verify PASS", self.progress)
        self.assertIn("| BLK-004 | P0 | Technical extraction accepted under resource-aware", self.progress)
        self.assertIn("| `CLOSED` |", next(line for line in self.progress.splitlines() if line.startswith("| BLK-003 |")))
        self.assertIn("| `CLOSED` |", next(line for line in self.progress.splitlines() if line.startswith("| BLK-004 |")))
        blk006_line = next(line for line in self.progress.splitlines() if line.startswith("| BLK-006 |"))
        blk007_line = next(line for line in self.progress.splitlines() if line.startswith("| BLK-007 |"))
        self.assertIn("| `CLOSED` |", blk006_line)
        self.assertIn("| `CLOSED` |", blk007_line)
        self.assertIn("open P0 blockers 0", self.progress)
        self.assertIn("Toàn bộ BLK-001..BLK-010 hiện CLOSED", self.progress)
        expected_governance_statuses = {
            "BLK-008": "CLOSED",
            "BLK-009": "CLOSED",
            "BLK-010": "CLOSED",
        }
        for blocker_id, expected_status in expected_governance_statuses.items():
            line = next(line for line in self.progress.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertIn(f"| `{expected_status}` |", line)

    def test_required_mapping_template_has_exact_12_codes_and_no_fake_ids(self) -> None:
        self.assertEqual({row["document_code"] for row in self.mapping_rows}, REQUIRED_CODES)
        self.assertEqual(len(self.mapping_rows), 12)
        for row in self.mapping_rows:
            self.assertEqual(row["required_authoritative_drive_file_id"], "REQUIRED")
            self.assertEqual(row["status"], "AWAITING_AUTHORITATIVE_MAPPING")
            self.assertEqual(row["required_binary_sha256"], "REQUIRED_AFTER_DOWNLOAD")
            self.assertEqual(row["required_parse_evidence"], "REQUIRED_AFTER_PARSE")
            self.assertEqual(row["required_human_reviewer"], "REQUIRED")

    def test_checkpoint_defines_live_gate_exclusions(self) -> None:
        self.assertIn("Allowed after exact approval", self.checkpoint)
        self.assertIn("Explicitly excluded until a later separate approval", self.checkpoint)
        self.assertIn("Supabase data/schema writes", self.checkpoint)
        self.assertIn("n8n publish/unpublish/archive", self.checkpoint)
        self.assertIn("Git commit/push/PR", self.checkpoint)

    def test_workflow_p_contract_remains_fail_closed(self) -> None:
        self.assertEqual(self.contract["live_status"], "SOURCE_ONLY_NOT_DEPLOYED")
        self.assertEqual(self.contract["production_write_default"], "DENY")
        self.assertEqual(self.contract["handoff_decision"]["blk004_status"], "OPEN")
        self.assertTrue(self.contract["table_candidate_contract"]["human_qa_required_before_indexing"])
        self.assertEqual(self.contract["table_candidate_contract"]["status"], "REVIEW_CANDIDATE_NOT_APPROVED_TRUTH")

    def test_manifest_records_no_live_operations(self) -> None:
        self.assertEqual(self.manifest["status"], "APPROVED_PENDING_AUTHORITATIVE_MAPPING")
        self.assertEqual(self.manifest["decision"], "APPROVED_PENDING_INPUT")
        self.assertEqual(self.manifest["supabase"]["operations"], [])
        self.assertEqual(self.manifest["n8n"]["operations"], [])
        self.assertFalse(self.manifest["approvalsReceived"][0]["consumed"])
        self.assertIn("Separate later approval for any Supabase write/import/indexing", self.manifest["approvalsRequired"])


if __name__ == "__main__":
    unittest.main()
