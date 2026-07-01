#!/usr/bin/env python3
"""Static assertions for R05-A11 all-open P0 blocker checks."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A11-p0-all-open-checks.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A11-p0-all-open-checks-manifest.json"
MAPPING_TEMPLATE = ROOT / "work/r05_a10_authoritative_mapping_required.csv"
CHAT_INDEX = ROOT / "docs/progress/CHAT_INDEX.md"
UPG_PLAN = ROOT / "docs/progress/UPG_CHAT_PLAN.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"
INTAKE_SCRIPT = ROOT / "scripts/r05_authoritative_corpus_intake.py"
INTAKE_REPORT = ROOT / "work/r05_authoritative_corpus_intake_current_report.json"


REQUIRED_CODES = {
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
}


class R05A11P0AllOpenChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.chat_index = CHAT_INDEX.read_text(encoding="utf-8")
        cls.upg_plan = UPG_PLAN.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")
        with MAPPING_TEMPLATE.open(encoding="utf-8", newline="") as handle:
            cls.mapping_rows = list(csv.DictReader(handle))

    def test_progress_tracks_r05_a25_after_actual_filename_parse_gate(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)
        self.assertIn("| R05-A11 |", self.progress)
        r05_a11_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A11 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a11_line)
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

    def test_current_remaining_p0_blockers_are_open(self) -> None:
        for blocker_id in ("BLK-001", "BLK-002", "BLK-003", "BLK-004", "BLK-005", "BLK-006", "BLK-007"):
            line = next(line for line in self.progress.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertIn("| P0 |", line)
            self.assertIn("| `CLOSED` |", line)
        blk004_line = next(line for line in self.progress.splitlines() if line.startswith("| BLK-004 |"))
        self.assertIn("| `CLOSED` |", blk004_line)
        self.assertIn("resource-aware", blk004_line)
        expected_governance_statuses = {
            "BLK-008": "CLOSED",
            "BLK-009": "CLOSED",
            "BLK-010": "CLOSED",
        }
        for blocker_id, expected_status in expected_governance_statuses.items():
            line = next(line for line in self.progress.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertIn(f"| `{expected_status}` |", line)

    def test_secondary_blocker_tracker_matches_p0_statuses(self) -> None:
        expected_statuses = {
            "BLK-001": "CLOSED",
            "BLK-002": "CLOSED",
            "BLK-003": "CLOSED",
            "BLK-004": "CLOSED",
            "BLK-005": "CLOSED",
            "BLK-006": "CLOSED",
            "BLK-007": "CLOSED",
            "BLK-008": "CLOSED",
            "BLK-009": "CLOSED",
            "BLK-010": "CLOSED",
        }
        for blocker_id, expected_status in expected_statuses.items():
            line = next(line for line in self.blockers.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertTrue(line.rstrip().endswith(f"| {expected_status} |"), line)

    def test_p0_final_check_is_not_opened(self) -> None:
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)
        self.assertIn("active_action: R08-A02", self.progress)
        p0_final_line = next(line for line in self.progress.splitlines() if line.startswith("| P0-FINAL-CHECK |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", p0_final_line)
        self.assertIn("FINAL_CHECK_PASS", p0_final_line)
        self.assertIn("No production GO", p0_final_line)

    def test_mapping_template_still_requires_authoritative_input(self) -> None:
        self.assertEqual({row["document_code"] for row in self.mapping_rows}, REQUIRED_CODES)
        self.assertEqual(len(self.mapping_rows), 12)
        self.assertTrue(all(row["required_authoritative_drive_file_id"] == "REQUIRED" for row in self.mapping_rows))
        self.assertIn("unconsumed because the authoritative mapping", self.checkpoint)
        self.assertIn("local-only intake validator", self.checkpoint)

    def test_authoritative_mapping_and_actual_filename_corpus_still_fail_strict_intake(self) -> None:
        result = subprocess.run(
            [sys.executable, str(INTAKE_SCRIPT), "--mapping-csv", str(MAPPING_TEMPLATE)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED")
        self.assertEqual(report["remote_operations"]["supabase"], [])
        self.assertEqual(report["remote_operations"]["n8n"], [])
        self.assertIn("GMP-SOP-001 has no authoritative Drive file ID", "\n".join(report["errors"]))
        retained_report = json.loads(INTAKE_REPORT.read_text(encoding="utf-8"))
        self.assertFalse(retained_report["ok"])
        self.assertEqual(retained_report["decision"], "FAIL_CLOSED")
        self.assertEqual(retained_report["record_count"], 0)
        self.assertEqual(retained_report["mode"], "corpus_dir_original_filename_mapping")
        retained_errors = "\n".join(retained_report["errors"])
        self.assertIn("status must be exactly 'AUTHORITATIVE_CONFIRMED'", retained_errors)
        self.assertIn("Missing required document codes", retained_errors)
        self.assertNotIn("do not match any required document code", retained_errors)
        identity_report = json.loads((ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json").read_text(encoding="utf-8"))
        self.assertFalse(identity_report["ok"])
        self.assertEqual(identity_report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        parse_report = json.loads((ROOT / "work/r05_a25_actual_filename_parse_evidence_report.json").read_text(encoding="utf-8"))
        self.assertEqual(parse_report["summary"]["pdf_file_count"], 12)
        self.assertEqual(parse_report["summary"]["parse_ready_records"], 11)
        self.assertEqual(parse_report["summary"]["parse_review_required_records"], 1)

    def test_u10_to_u15_are_not_claimed_pass(self) -> None:
        for chat in ("UPG-CHAT-10", "UPG-CHAT-11", "UPG-CHAT-13", "UPG-CHAT-14", "UPG-CHAT-15"):
            line = next(line for line in self.chat_index.splitlines() if line.startswith(f"| {chat} |"))
            self.assertIn("| Not started |", line)
        u16_line = next(line for line in self.chat_index.splitlines() if line.startswith("| UPG-CHAT-16 |"))
        self.assertIn("| Blocked by design |", u16_line)
        self.assertIn("U10–15 PASS", self.upg_plan)

    def test_manifest_records_no_live_operations_and_hold(self) -> None:
        self.assertEqual(self.manifest["rhythm"], "R05-A11")
        self.assertEqual(self.manifest["decision"], "HOLD")
        self.assertEqual(self.manifest["supabase"]["operations"], [])
        self.assertEqual(self.manifest["n8n"]["operations"], [])
        self.assertEqual(self.manifest["approvalsConsumed"], [])
        self.assertEqual(self.manifest["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-004"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-006"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-007"], "OPEN")
        self.assertIn("scripts/r05_authoritative_corpus_intake.py", self.manifest["createdFiles"])
        self.assertIn("work/r05_authoritative_corpus_intake_current_report.json", self.manifest["sourceEvidence"])


if __name__ == "__main__":
    unittest.main()
