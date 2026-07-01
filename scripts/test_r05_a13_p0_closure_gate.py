#!/usr/bin/env python3
"""Tests for the R05-A13 remaining P0 closure gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a13_p0_closure_gate.py"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A13-authoritative-corpus-prerequisite-gate.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A13-authoritative-corpus-prerequisite-gate-manifest.json"
REPORT = ROOT / "work/r05_a13_p0_closure_gate_current_report.json"
A24_REPORT = ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json"
A25_REPORT = ROOT / "work/r05_a25_actual_filename_parse_evidence_report.json"

REQUIRED_CODES = [
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
]


def run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class R05A13P0ClosureGateTest(unittest.TestCase):
    def test_default_gate_fails_closed_when_actual_filenames_have_no_owner_mapping(self) -> None:
        result = run_gate()

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        identity_report = json.loads(A24_REPORT.read_text(encoding="utf-8"))
        parse_report = json.loads(A25_REPORT.read_text(encoding="utf-8"))

        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED_INPUT_REQUIRED")
        self.assertEqual(report["remote_operations"]["supabase"], [])
        self.assertEqual(report["remote_operations"]["n8n"], [])
        self.assertEqual(report["remote_operations"]["git"], [])
        self.assertEqual(report["blockers"]["BLK-003"], "OPEN")
        self.assertTrue(report["input_checks"][0]["exists"])
        self.assertEqual(report["input_checks"][0]["decision"], "FAIL_CLOSED")
        self.assertEqual(report["input_checks"][0]["record_count"], 12)
        self.assertIn("has no authoritative Drive file ID", " ".join(report["input_checks"][0]["errors"]))
        self.assertEqual(report["input_checks"][1]["mode"], "corpus_dir")
        self.assertEqual(report["input_checks"][1]["decision"], "FAIL_CLOSED")
        self.assertEqual(report["input_checks"][1]["record_count"], 0)
        self.assertIn("do not match any required document code", " ".join(report["input_checks"][1]["errors"]))
        self.assertIn("Do not execute citation runtime", " ".join(report["next_allowed_local_steps"]))
        self.assertEqual(identity_report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        self.assertEqual(identity_report["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(parse_report["summary"]["pdf_file_count"], 12)
        self.assertEqual(parse_report["decision"], "FAIL_CLOSED_PARSE_REVIEW_REQUIRED")

    def test_valid_mapping_makes_gate_ready_for_controlled_plan_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_path = Path(temp_dir) / "mapping.csv"
            corpus_dir = Path(temp_dir) / "missing-corpus"
            with mapping_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["document_code", "drive_file_id", "status", "file_name", "mime_type"],
                )
                writer.writeheader()
                for idx, code in enumerate(REQUIRED_CODES, start=1):
                    writer.writerow(
                        {
                            "document_code": code,
                            "drive_file_id": f"1AuthoritativeDriveId{idx:02d}",
                            "status": "AUTHORITATIVE_CONFIRMED",
                            "file_name": f"{code}.pdf",
                            "mime_type": "application/pdf",
                        }
                    )

            result = run_gate("--mapping-csv", str(mapping_path), "--corpus-dir", str(corpus_dir))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["decision"], "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN")
        self.assertEqual(report["blockers"]["BLK-003"], "OPEN")
        self.assertIn("not closed yet", report["rationale"])

    def test_valid_local_corpus_makes_gate_ready_without_remote_ops(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir) / "corpus"
            corpus_dir.mkdir()
            mapping_path = Path(temp_dir) / "missing-mapping.csv"
            for code in REQUIRED_CODES:
                (corpus_dir / f"{code} authoritative source.pdf").write_bytes(
                    b"%PDF-1.7\n" + code.encode("ascii") + b"\n%%EOF\n"
                )

            result = run_gate("--mapping-csv", str(mapping_path), "--corpus-dir", str(corpus_dir))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["input_checks"][1]["mode"], "corpus_dir")
        self.assertEqual(report["input_checks"][1]["record_count"], 12)
        self.assertEqual(report["remote_operations"]["supabase"], [])
        self.assertEqual(report["remote_operations"]["n8n"], [])

    def test_checkpoint_manifest_and_retained_report_match_fail_closed_state(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertIn("FAIL_CLOSED_INPUT_REQUIRED", checkpoint)
        self.assertEqual(manifest["rhythm"], "R05-A13")
        self.assertEqual(manifest["decision"], "FAIL_CLOSED_INPUT_REQUIRED")
        self.assertEqual(manifest["supabase"]["operations"], [])
        self.assertEqual(manifest["n8n"]["operations"], [])
        self.assertEqual(manifest["git"]["operations"], [])
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED_INPUT_REQUIRED")
        self.assertTrue(report["input_checks"][0]["exists"])
        self.assertEqual(report["input_checks"][0]["decision"], "FAIL_CLOSED")
        self.assertEqual(report["blockers"]["BLK-006"], "OPEN")
        self.assertEqual(report["blockers"]["BLK-007"], "OPEN")


if __name__ == "__main__":
    unittest.main()
