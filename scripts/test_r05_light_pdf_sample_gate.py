#!/usr/bin/env python3
"""Tests for the R05 light-PDF sample probe gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_light_pdf_sample_gate.py"
SAMPLE_CSV = ROOT / "work/r05_random_light_pdf_sample_set.csv"
INVENTORY_CSV = ROOT / "work/r05_a03_drive_metadata_inventory.csv"


def run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class R05LightPdfSampleGateTest(unittest.TestCase):
    def test_current_sample_set_is_ready_for_approval_only(self) -> None:
        result = run_gate(
            "--sample-csv",
            str(SAMPLE_CSV),
            "--inventory-csv",
            str(INVENTORY_CSV),
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["decision"], "READY_FOR_APPROVAL")
        self.assertEqual(report["row_count"], 12)
        self.assertEqual(report["execution_controls"]["supabase_writes"], "DENY")
        self.assertEqual(report["execution_controls"]["authoritative_closure_claim"], "DENY")
        self.assertEqual(report["remote_operations"]["n8n"], [])
        self.assertTrue(all(record["mime_type"] == "application/pdf" for record in report["records"]))

    def test_authoritative_status_is_rejected_for_sample_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_csv = Path(temp_dir) / "bad.csv"
            with SAMPLE_CSV.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["Trạng thái"] = "AUTHORITATIVE_CONFIRMED"
            with bad_csv.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            result = run_gate("--sample-csv", str(bad_csv))

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED")
        self.assertIn("must not claim authoritative approval", "\n".join(report["errors"]))

    def test_duplicate_or_heavy_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_csv = Path(temp_dir) / "bad.csv"
            with SAMPLE_CSV.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[1]["ID"] = rows[0]["ID"]
            rows[2]["size_bytes"] = str(1024 * 1024 + 1)
            with bad_csv.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            result = run_gate("--sample-csv", str(bad_csv))

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        joined_errors = "\n".join(report["errors"])
        self.assertIn("duplicate Drive file ID", joined_errors)
        self.assertIn("exceeds max", joined_errors)


if __name__ == "__main__":
    unittest.main()
