#!/usr/bin/env python3
"""Tests for the R05-A18 authoritative-input readiness operator."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a18_authoritative_input_readiness.py"
REPORT = ROOT / "work/r05_a18_authoritative_input_readiness_report.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A18-authoritative-input-readiness.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A18-authoritative-input-readiness-manifest.json"
A24_REPORT = ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json"
A25_REPORT = ROOT / "work/r05_a25_actual_filename_parse_evidence_report.json"
REQUIRED_CODES = [
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
]


def run_operator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_valid_mapping(path: Path, id_column: str = "drive_file_id") -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["document_code", id_column, "status", "file_name", "mime_type"],
        )
        writer.writeheader()
        for index, code in enumerate(REQUIRED_CODES, start=1):
            writer.writerow(
                {
                    "document_code": code,
                    id_column: f"1ExactAuthoritativeDriveId{index:02d}",
                    "status": "AUTHORITATIVE_CONFIRMED",
                    "file_name": f"{code}.pdf",
                    "mime_type": "application/pdf",
                }
            )


class R05A18AuthoritativeInputReadinessTest(unittest.TestCase):
    def test_default_repository_state_fails_closed_but_actual_filename_parse_evidence_exists(self) -> None:
        result = run_operator()

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        identity_report = json.loads(A24_REPORT.read_text(encoding="utf-8"))
        parse_report = json.loads(A25_REPORT.read_text(encoding="utf-8"))

        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED_INPUT_REQUIRED")
        self.assertEqual(report["inputs"]["mapping_csv"]["row_count"], 12)
        self.assertEqual(report["inputs"]["mapping_csv"]["authoritative_confirmed_count"], 0)
        self.assertEqual(report["inputs"]["mapping_csv"]["concrete_drive_id_count"], 0)
        self.assertTrue(report["inputs"]["corpus_dir"]["exists"])
        self.assertEqual(report["inputs"]["corpus_dir"]["file_count"], 12)
        self.assertEqual(report["inputs"]["corpus_dir"]["intake"]["record_count"], 0)
        self.assertEqual(report["valid_input_modes"], [])
        self.assertTrue(report["prior_accession"]["quality_boundary_preserved"])
        self.assertEqual(report["quality_controls"]["rejected_a17_candidates_promoted"], 0)
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertEqual(identity_report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        self.assertEqual(identity_report["blockers"]["BLK-004"], "OPEN")
        self.assertEqual(parse_report["summary"]["pdf_file_count"], 12)
        self.assertEqual(parse_report["summary"]["parse_ready_records"], 11)
        self.assertEqual(parse_report["summary"]["parse_review_required_records"], 1)

    def test_valid_mapping_is_plan_ready_but_does_not_close_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping = Path(temp_dir) / "mapping.csv"
            missing_corpus = Path(temp_dir) / "missing-corpus"
            output = Path(temp_dir) / "report.json"
            write_valid_mapping(mapping)

            result = run_operator(
                "--mapping-csv",
                str(mapping),
                "--corpus-dir",
                str(missing_corpus),
                "--output",
                str(output),
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["valid_input_modes"], ["mapping_csv"])
        self.assertEqual(report["decision"], "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN")
        self.assertEqual(report["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(len(report["input_fingerprint"]), 64)
        self.assertFalse(report["freshness"]["baseline_available"])

    def test_authoritative_drive_id_alias_is_counted_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping = Path(temp_dir) / "mapping.csv"
            missing_corpus = Path(temp_dir) / "missing-corpus"
            write_valid_mapping(mapping, id_column="authoritative_drive_file_id")

            result = run_operator(
                "--mapping-csv",
                str(mapping),
                "--corpus-dir",
                str(missing_corpus),
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["inputs"]["mapping_csv"]["concrete_drive_id_count"], 12)
        self.assertEqual(report["valid_input_modes"], ["mapping_csv"])

    def test_second_run_records_unchanged_input_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping = Path(temp_dir) / "mapping.csv"
            missing_corpus = Path(temp_dir) / "missing-corpus"
            output = Path(temp_dir) / "report.json"
            write_valid_mapping(mapping)
            args = (
                "--mapping-csv",
                str(mapping),
                "--corpus-dir",
                str(missing_corpus),
                "--output",
                str(output),
            )

            first = run_operator(*args)
            second = run_operator(*args)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        report = json.loads(second.stdout)
        self.assertTrue(report["freshness"]["baseline_available"])
        self.assertFalse(report["freshness"]["changed_since_previous"])

    def test_retained_artifacts_match_current_fail_closed_state(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")

        self.assertEqual(report["rhythm"], "R05-A18")
        self.assertEqual(report["decision"], "FAIL_CLOSED_INPUT_REQUIRED")
        self.assertEqual(report["blockers"]["BLK-006"], "OPEN")
        self.assertIn("FAIL_CLOSED_INPUT_REQUIRED", checkpoint)
        self.assertEqual(manifest["decision"], report["decision"])
        self.assertEqual(manifest["n8n"]["operations"], [])
        self.assertEqual(manifest["supabase"]["operations"], [])
        self.assertEqual(manifest["git"]["operations"], [])


if __name__ == "__main__":
    unittest.main()
