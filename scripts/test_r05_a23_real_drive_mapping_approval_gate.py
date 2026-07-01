#!/usr/bin/env python3
"""Tests for the R05-A23 real Drive mapping approval gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a23_real_drive_mapping_approval_gate.py"
REPORT = ROOT / "work/r05_a23_real_drive_mapping_approval_gate_report.json"
REQUIRED_TEMPLATE = ROOT / "work/r05_a23_owner_confirmed_drive_mapping_required.csv"
APPROVAL_REQUEST = ROOT / "work/r05_a23_controlled_download_hash_parse_approval_request.md"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A23-real-drive-mapping-approval-gate.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A23-real-drive-mapping-approval-gate-manifest.json"

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


def write_owner_confirmed_mapping(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["document_code", "drive_file_id", "status", "file_name", "mime_type"],
        )
        writer.writeheader()
        for index, code in enumerate(REQUIRED_CODES, start=1):
            writer.writerow({
                "document_code": code,
                "drive_file_id": f"1OwnerConfirmedCraveDriveId{index:02d}AaBbCcDdEe",
                "status": "AUTHORITATIVE_CONFIRMED",
                "file_name": f"{code}.pdf",
                "mime_type": "application/pdf",
            })


class R05A23RealDriveMappingApprovalGateTest(unittest.TestCase):
    def test_default_repository_mapping_fails_closed_and_writes_request_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            result = run_operator(
                "--required-template",
                str(base / "required.csv"),
                "--approval-request",
                str(base / "approval.md"),
                "--output",
                str(base / "report.json"),
            )
            report = json.loads((base / "report.json").read_text(encoding="utf-8"))
            approval = (base / "approval.md").read_text(encoding="utf-8")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED_REAL_DRIVE_IDS_REQUIRED")
        self.assertEqual(report["inputs"]["real_mapping_csv"]["row_count"], 12)
        self.assertEqual(report["inputs"]["real_mapping_csv"]["concrete_drive_id_count"], 0)
        self.assertEqual(report["inputs"]["real_mapping_csv"]["placeholder_drive_id_count"], 12)
        self.assertEqual(report["approval_request"]["status"], "NOT_READY_DO_NOT_APPROVE_YET")
        self.assertIn("STATUS: NOT_READY_DO_NOT_APPROVE_YET", approval)
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertFalse(report["download_allowed_now"])
        self.assertFalse(report["download_allowed_after_fresh_approval"])

    def test_a22_simulated_mapping_is_rejected_by_strict_real_id_check(self) -> None:
        result = run_operator(
            "--real-mapping",
            str(ROOT / "work/r05_a22_simulated_authoritative_drive_mapping.csv"),
        )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        retained_report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["decision"], "FAIL_CLOSED_REAL_DRIVE_IDS_REQUIRED")
        self.assertGreaterEqual(retained_report["inputs"]["real_mapping_csv"]["synthetic_drive_id_count"], 12)
        self.assertIn(
            "simulated/synthetic",
            " ".join(retained_report["inputs"]["real_mapping_csv"]["strict_real_id_check"]["errors"]),
        )

    def test_owner_confirmed_mapping_becomes_ready_for_separate_approval_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            mapping = base / "mapping.csv"
            output = base / "report.json"
            approval = base / "approval.md"
            required = base / "required.csv"
            write_owner_confirmed_mapping(mapping)

            result = run_operator(
                "--real-mapping",
                str(mapping),
                "--required-template",
                str(required),
                "--approval-request",
                str(approval),
                "--output",
                str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            approval_text = approval.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report["ok"])
        self.assertEqual(report["decision"], "READY_FOR_CONTROLLED_DOWNLOAD_HASH_PARSE_APPROVAL")
        self.assertEqual(report["inputs"]["real_mapping_csv"]["concrete_drive_id_count"], 12)
        self.assertEqual(report["inputs"]["real_mapping_csv"]["synthetic_drive_id_count"], 0)
        self.assertTrue(report["download_allowed_after_fresh_approval"])
        self.assertFalse(report["download_allowed_now"])
        self.assertIn("STATUS: READY_TO_REQUEST_APPROVAL", approval_text)
        self.assertIn("one-file-per-execution/concurrency 1", approval_text)
        self.assertIn("khong Supabase write/import/indexing", approval_text)
        self.assertIn("khong chunk/embed", approval_text)
        self.assertIn("khong publish/archive/update production workflow", approval_text)
        self.assertIn("khong Git remote", approval_text)

    def test_required_template_has_exact_codes_and_explicit_placeholders(self) -> None:
        run_operator()

        with REQUIRED_TEMPLATE.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual([row["document_code"] for row in rows], REQUIRED_CODES)
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row["drive_file_id"] == "REPLACE_WITH_OWNER_CONFIRMED_DRIVE_FILE_ID" for row in rows))
        self.assertTrue(all(row["status"] == "AWAITING_OWNER_CONFIRMED_DRIVE_ID" for row in rows))
        self.assertTrue(all(row["mime_type"] == "application/pdf" for row in rows))

    def test_retained_checkpoint_manifest_and_report_match_fail_closed_state(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        approval = APPROVAL_REQUEST.read_text(encoding="utf-8")

        self.assertEqual(report["rhythm"], "R05-A23")
        self.assertEqual(report["decision"], "FAIL_CLOSED_REAL_DRIVE_IDS_REQUIRED")
        self.assertEqual(report["approval_request"]["status"], "NOT_READY_DO_NOT_APPROVE_YET")
        self.assertIn("FAIL_CLOSED_REAL_DRIVE_IDS_REQUIRED", checkpoint)
        self.assertIn("STATUS: NOT_READY_DO_NOT_APPROVE_YET", approval)
        self.assertEqual(manifest["rhythm"], "R05-A23")
        self.assertEqual(manifest["decision"], report["decision"])
        self.assertEqual(manifest["supabase"]["operations"], [])
        self.assertEqual(manifest["n8n"]["operations"], [])
        self.assertEqual(manifest["git"]["operations"], [])
        self.assertEqual(manifest["blockers"]["BLK-003"], "OPEN")


if __name__ == "__main__":
    unittest.main()
