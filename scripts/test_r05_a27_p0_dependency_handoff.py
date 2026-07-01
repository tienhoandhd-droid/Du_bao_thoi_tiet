#!/usr/bin/env python3
"""Kiểm thử gate fail-closed dependency handoff R05-A27."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a27_p0_dependency_handoff.py"
REPORT = ROOT / "work/r05_a27_p0_dependency_handoff_report.json"


def run_operator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class R05A27P0DependencyHandoffTest(unittest.TestCase):
    def test_default_state_fails_closed_and_exposes_cross_package_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            result = run_operator("--output", str(output))
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED_P0_DEPENDENCY_HANDOFF_REQUIRED")
        self.assertEqual(report["identity"]["a24_summary"]["records_requiring_catalog_reconciliation"], 0)
        self.assertEqual(report["identity"]["catalog_decisions"]["pending_decisions"], 12)
        self.assertEqual(report["human_review"]["corpus"]["pending_reviews"], 12)
        self.assertEqual(report["human_review"]["ocr_pages"]["pending_reviews"], 5)
        self.assertTrue(report["source_contract_checks"]["chunk_document_version_fk_has_deploy_migration"])
        self.assertTrue(report["source_contract_checks"]["chunk_document_version_fk_exists_in_architecture_draft"])
        impacts = {item["item"]: item["effect"] for item in report["dependency_impacts"]}
        self.assertEqual(impacts["BLK-005 / 65 embeddings"], "HISTORICAL_BASELINE_REVALIDATION_REQUIRED")
        self.assertEqual(impacts["R07-A01/A02 table/figure designs"], "SAFE_DESIGN_ONLY_IMPLEMENTATION_BLOCKED")
        self.assertFalse(report["p0_final_check_allowed"])
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})

    def test_ai_reviewer_cannot_complete_accountable_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            queue = base / "review.csv"
            with queue.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "file_name", "source_sha256", "mapping_status",
                        "reviewer_name", "reviewer_role", "review_status",
                        "reviewed_at", "reviewer_decision", "reviewer_notes", "auto_approve",
                    ],
                )
                writer.writeheader()
                writer.writerow({
                    "file_name": "GMP-SOP-001.pdf",
                    "source_sha256": "a" * 64,
                    "mapping_status": "AUTHORITATIVE_CONFIRMED",
                    "reviewer_name": "Codex AI",
                    "reviewer_role": "QA bot",
                    "review_status": "COMPLETED_ACCOUNTABLE_HUMAN_REVIEW",
                    "reviewed_at": "2026-06-30T17:00:00+07:00",
                    "reviewer_decision": "APPROVED",
                    "reviewer_notes": "Automated approval is forbidden.",
                    "auto_approve": "FALSE",
                })

            sys.path.insert(0, str(ROOT / "scripts"))
            import r05_a27_p0_dependency_handoff as gate
            result = gate.validate_review_queue(queue, expected_rows=1, page_queue=False)

        self.assertFalse(result["ready"])
        self.assertIn("reviewer con người chịu trách nhiệm", "\n".join(result["errors"]))

    def test_retained_report_matches_expected_fail_closed_state(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertEqual(report["rhythm"], "R05-A27")
        self.assertEqual(report["decision"], "FAIL_CLOSED_P0_DEPENDENCY_HANDOFF_REQUIRED")
        self.assertFalse(report["p0_final_check_allowed"])
        self.assertEqual(report["identity"]["catalog_decisions"]["row_count"], 12)
        self.assertEqual(report["human_review"]["corpus"]["row_count"], 12)
        self.assertEqual(report["human_review"]["ocr_pages"]["row_count"], 5)
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})


if __name__ == "__main__":
    unittest.main()
