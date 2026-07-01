#!/usr/bin/env python3
"""Tests for the R05-A21 simulated owner-promotion readiness lane."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a21_simulated_promotion_readiness.py"
CURRENT_A20_REPORT = ROOT / "work/r05_a20_owner_promotion_gate_report.json"
CURRENT_A20_PLAN = ROOT / "work/r05_a20_owner_promotion_plan.csv"
REAL_CORRECTED_CORPUS = ROOT / "work/r05_authoritative_corpus"
A24_REPORT = ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json"
A25_REPORT = ROOT / "work/r05_a25_actual_filename_parse_evidence_report.json"


def run_simulation(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class R05A21SimulatedPromotionReadinessTest(unittest.TestCase):
    def test_simulated_positive_path_reaches_readiness_without_real_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            plan = base / "simulated_plan.csv"
            corpus = base / "simulated_corpus"
            a20_output = base / "simulated_a20_report.json"
            output = base / "simulated_a21_report.json"

            result = run_simulation(
                "--review-plan",
                str(plan),
                "--corpus-dir",
                str(corpus),
                "--a20-output",
                str(a20_output),
                "--output",
                str(output),
            )

            report = json.loads(output.read_text(encoding="utf-8"))
            a20_report = json.loads(a20_output.read_text(encoding="utf-8"))
            rows = read_csv(plan)
            pdfs = sorted(corpus.glob("*.pdf"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["rhythm"], "R05-A21")
        self.assertEqual(report["decision"], "SIMULATED_READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN")
        self.assertTrue(report["simulation_only"])
        self.assertEqual(report["authoritative_effect"], "DENY")
        self.assertFalse(report["production_import_allowed"])
        self.assertFalse(report["retrieval_enablement_allowed"])
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertEqual(report["blockers"], {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        })
        self.assertEqual(a20_report["decision"], "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN")
        self.assertEqual(a20_report["promotion_plan"]["summary"]["complete_human_approved_rows"], 12)
        self.assertEqual(len(a20_report["corrected_corpus"]["records"]), 12)
        self.assertEqual(len(rows), 12)
        self.assertEqual(len(pdfs), 12)
        self.assertTrue(all("SIMULATED_ONLY_NOT_AUTHORITATIVE" in row["promotion_notes"] for row in rows))
        self.assertNotEqual(Path(report["simulation"]["corpus_dir"]), REAL_CORRECTED_CORPUS)

    def test_retained_a20_real_gate_remains_fail_closed(self) -> None:
        report = json.loads(CURRENT_A20_REPORT.read_text(encoding="utf-8"))
        identity_report = json.loads(A24_REPORT.read_text(encoding="utf-8"))
        parse_report = json.loads(A25_REPORT.read_text(encoding="utf-8"))
        rows = read_csv(CURRENT_A20_PLAN)

        self.assertEqual(report["decision"], "FAIL_CLOSED_OWNER_APPROVAL_REQUIRED")
        self.assertEqual(report["promotion_plan"]["summary"]["complete_human_approved_rows"], 0)
        self.assertTrue(all(row["technical_sme_decision"] == "PENDING" for row in rows))
        self.assertTrue(REAL_CORRECTED_CORPUS.exists())
        self.assertEqual(identity_report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        self.assertEqual(identity_report["summary"]["audit_source"], "actual_filename_unmapped_pdfs")
        self.assertEqual(identity_report["summary"]["intake_record_count"], 0)
        self.assertEqual(identity_report["summary"]["record_count"], 12)
        self.assertEqual(identity_report["summary"]["records_identity_fail_closed"], 12)
        self.assertEqual(parse_report["summary"]["pdf_file_count"], 12)
        self.assertEqual(parse_report["blockers"]["BLK-004"], "OPEN_PARSE_EVIDENCE_RECORDED_NOT_CLOSED")


if __name__ == "__main__":
    unittest.main()
