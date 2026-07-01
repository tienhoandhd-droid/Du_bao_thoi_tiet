#!/usr/bin/env python3
"""Tests for the R05-A22 simulated authoritative Drive mapping lane."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a22_simulated_authoritative_drive_mapping.py"
INTAKE_SCRIPT = ROOT / "scripts/r05_authoritative_corpus_intake.py"
REAL_MAPPING = ROOT / "work/r05_authoritative_12_file_mapping.csv"
REAL_CORRECTED_CORPUS = ROOT / "work/r05_authoritative_corpus"
A24_REPORT = ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json"


def run_operator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_intake(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INTAKE_SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class R05A22SimulatedAuthoritativeDriveMappingTest(unittest.TestCase):
    def test_simulated_mapping_passes_intake_shape_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            mapping = base / "simulated_mapping.csv"
            intake_report = base / "intake_report.json"
            output = base / "a22_report.json"

            result = run_operator(
                "--mapping-csv",
                str(mapping),
                "--intake-report",
                str(intake_report),
                "--output",
                str(output),
            )

            report = json.loads(output.read_text(encoding="utf-8"))
            intake = json.loads(intake_report.read_text(encoding="utf-8"))
            rows = read_csv(mapping)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["decision"], "SIMULATED_AUTHORITATIVE_DRIVE_MAPPING_INTAKE_PASS")
        self.assertTrue(report["simulation_only"])
        self.assertEqual(report["authoritative_effect"], "DENY")
        self.assertFalse(report["download_allowed"])
        self.assertFalse(report["production_import_allowed"])
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertEqual(report["blockers"], {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        })
        self.assertTrue(intake["ok"])
        self.assertEqual(intake["decision"], "PASS")
        self.assertEqual(intake["mode"], "mapping_csv")
        self.assertEqual(intake["record_count"], 12)
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row["status"] == "AUTHORITATIVE_CONFIRMED" for row in rows))
        self.assertTrue(all(row["mime_type"] == "application/pdf" for row in rows))
        self.assertTrue(all(row["simulation_notice"] == "SIMULATED_ONLY_NOT_AUTHORITATIVE_DO_NOT_DOWNLOAD_OR_IMPORT" for row in rows))

    def test_real_mapping_template_remains_placeholder_fail_closed(self) -> None:
        result = run_intake("--mapping-csv", str(REAL_MAPPING))
        identity_report = json.loads(A24_REPORT.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED")
        self.assertIn("has no authoritative Drive file ID", "\n".join(report["errors"]))
        self.assertTrue(REAL_CORRECTED_CORPUS.exists())
        self.assertEqual(identity_report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        self.assertEqual(identity_report["blockers"]["BLK-003"], "OPEN")


if __name__ == "__main__":
    unittest.main()
