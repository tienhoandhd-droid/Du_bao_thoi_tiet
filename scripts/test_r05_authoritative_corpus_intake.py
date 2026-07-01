#!/usr/bin/env python3
"""Tests for the R05 authoritative 12-file corpus intake gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_authoritative_corpus_intake.py"
TEMPLATE = ROOT / "work/r05_a10_authoritative_mapping_required.csv"

REQUIRED_CODES = [
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
]


def run_intake(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def authoritative_mapping_rows() -> list[dict[str, str]]:
    return [
        {
            "document_code": code,
            "drive_file_id": f"1AuthoritativeDriveId{idx:02d}",
            "status": "AUTHORITATIVE_CONFIRMED",
            "file_name": f"{code}.pdf",
            "mime_type": "application/pdf",
        }
        for idx, code in enumerate(REQUIRED_CODES, start=1)
    ]


def write_mapping(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class R05AuthoritativeCorpusIntakeTest(unittest.TestCase):
    def test_existing_placeholder_template_fails_closed(self) -> None:
        result = run_intake("--mapping-csv", str(TEMPLATE))

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED")
        self.assertIn("GMP-SOP-001 has no authoritative Drive file ID", "\n".join(report["errors"]))

    def test_complete_mapping_passes_as_download_ready_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_path = Path(temp_dir) / "authoritative_mapping.csv"
            write_mapping(mapping_path, authoritative_mapping_rows())

            result = run_intake("--mapping-csv", str(mapping_path))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "mapping_csv")
        self.assertEqual(report["record_count"], 12)
        self.assertIn("controlled download", report["warnings"][0])

    def test_mapping_requires_exact_confirmed_status_and_pdf_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_path = Path(temp_dir) / "not_authoritative_mapping.csv"
            rows = authoritative_mapping_rows()
            rows[0]["status"] = "REVIEWED"
            rows[1]["file_name"] = "GMP-SOP-002.docx"
            rows[2]["mime_type"] = "application/octet-stream"
            write_mapping(mapping_path, rows)

            result = run_intake("--mapping-csv", str(mapping_path))

        self.assertNotEqual(result.returncode, 0)
        joined_errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("status must be exactly 'AUTHORITATIVE_CONFIRMED'", joined_errors)
        self.assertIn("file_name must end in .pdf", joined_errors)
        self.assertIn("mime_type must be 'application/pdf'", joined_errors)

    def test_duplicate_missing_and_archive_mapping_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_path = Path(temp_dir) / "bad_mapping.csv"
            rows = [
                {
                    "document_code": "GMP-SOP-001",
                    "drive_file_id": "same-id",
                    "status": "AUTHORITATIVE_CONFIRMED",
                    "file_name": "GMP-SOP-001.pdf",
                    "mime_type": "application/pdf",
                },
                {
                    "document_code": "GMP-SOP-001",
                    "drive_file_id": "same-id",
                    "status": "AUTHORITATIVE_CONFIRMED",
                    "file_name": "GMP-SOP-001-copy.pdf",
                    "mime_type": "application/pdf",
                },
                {
                    "document_code": "VQ-QT-003",
                    "drive_file_id": "rar-id",
                    "status": "AUTHORITATIVE_CONFIRMED",
                    "file_name": "TĐ QTSX 10.2024 - HUP.rar",
                    "mime_type": "application/x-rar",
                },
            ]
            with mapping_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            result = run_intake("--mapping-csv", str(mapping_path))

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        joined_errors = "\n".join(report["errors"])
        self.assertIn("duplicate document_code GMP-SOP-001", joined_errors)
        self.assertIn("archive-like file", joined_errors)
        self.assertIn("Missing required document codes", joined_errors)

    def test_corrected_local_corpus_folder_passes_and_hashes_12_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir) / "corpus"
            corpus_dir.mkdir()
            for code in REQUIRED_CODES:
                (corpus_dir / f"{code} authoritative source.pdf").write_bytes(
                    b"%PDF-1.7\n" + code.encode("ascii") + b"\n%%EOF\n"
                )
            output_path = Path(temp_dir) / "report.json"

            result = run_intake("--corpus-dir", str(corpus_dir), "--output", str(output_path))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "corpus_dir_filename_code_fallback")
        self.assertEqual(report["record_count"], 12)
        self.assertEqual({record["document_code"] for record in report["records"]}, set(REQUIRED_CODES))
        self.assertTrue(all(len(record["sha256"]) == 64 for record in report["records"]))

    def test_original_filenames_pass_with_separate_authoritative_mapping_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus_dir = base / "corpus"
            corpus_dir.mkdir()
            mapping_path = base / "local_mapping.csv"
            original_names = [
                "ISO 10993 source.pdf",
                "PDA TR 33.pdf",
                "PDA TR 34.pdf",
                "PDA TR 39.pdf",
                "PDA TR 40.pdf",
                "PDA TR 69.pdf",
                "PDA TR 70.pdf",
                "ISPE MACO.pdf",
                "Cleanroom Management.pdf",
                "ISO 8573-3.pdf",
                "ISO 8573-7.pdf",
                "WHO TRS source.pdf",
            ]
            rows: list[dict[str, str]] = []
            self.assertEqual(len(REQUIRED_CODES), len(original_names))
            for index, (code, file_name) in enumerate(zip(REQUIRED_CODES, original_names)):
                (corpus_dir / file_name).write_bytes(
                    b"%PDF-1.7\noriginal-source-" + str(index).encode("ascii") + b"\n%%EOF\n"
                )
                rows.append(
                    {
                        "document_code": code,
                        "file_name": file_name,
                        "status": "AUTHORITATIVE_CONFIRMED",
                        "mapping_notes": f"Owner-confirmed source identity for {code}",
                    }
                )
            write_mapping(mapping_path, rows)

            result = run_intake(
                "--corpus-dir",
                str(corpus_dir),
                "--local-mapping-csv",
                str(mapping_path),
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "corpus_dir_original_filename_mapping")
        self.assertEqual(report["record_count"], 12)
        self.assertTrue(
            all(record["identity_binding"] == "authoritative_local_mapping_manifest" for record in report["records"])
        )
        self.assertEqual(
            {record["original_file_name"] for record in report["records"]},
            set(original_names),
        )

    def test_original_filename_mapping_requires_authoritative_status_and_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus_dir = base / "corpus"
            corpus_dir.mkdir()
            mapping_path = base / "local_mapping.csv"
            rows: list[dict[str, str]] = []
            for code in REQUIRED_CODES:
                file_name = f"Original {code}.pdf"
                (corpus_dir / file_name).write_bytes(b"%PDF-1.7\nunique-" + code.encode("ascii") + b"\n%%EOF\n")
                rows.append(
                    {
                        "document_code": code,
                        "file_name": file_name,
                        "status": "PENDING_OWNER_CONFIRMATION",
                        "mapping_notes": "",
                    }
                )
            write_mapping(mapping_path, rows)

            result = run_intake(
                "--corpus-dir",
                str(corpus_dir),
                "--local-mapping-csv",
                str(mapping_path),
            )

        self.assertNotEqual(result.returncode, 0)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("status must be exactly 'AUTHORITATIVE_CONFIRMED'", errors)
        self.assertIn("mapping_notes must record the owner mapping basis", errors)

    def test_unrelated_reference_folder_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir) / "reference_library"
            corpus_dir.mkdir()
            (corpus_dir / "ISO 14644-6 2007 Cleanrooms_and.pdf").write_bytes(b"%PDF-1.7\nISO\n%%EOF\n")
            (corpus_dir / "USP_1223_validation.pdf").write_bytes(b"%PDF-1.7\nUSP\n%%EOF\n")

            result = run_intake("--corpus-dir", str(corpus_dir))

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        joined_errors = "\n".join(report["errors"])
        self.assertIn("do not match any required document code", joined_errors)
        self.assertIn("Missing required source file for GMP-SOP-001", joined_errors)

    def test_corrected_corpus_rejects_fake_pdf_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir) / "corpus"
            corpus_dir.mkdir()
            for code in REQUIRED_CODES:
                payload = b"not-a-pdf\n" if code == "GMP-SOP-001" else (
                    b"%PDF-1.7\n" + code.encode("ascii") + b"\n%%EOF\n"
                )
                (corpus_dir / f"{code}.pdf").write_bytes(payload)

            result = run_intake("--corpus-dir", str(corpus_dir))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not have a PDF signature", "\n".join(json.loads(result.stdout)["errors"]))

    def test_corrected_corpus_rejects_same_binary_renamed_for_two_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir) / "corpus"
            corpus_dir.mkdir()
            duplicate = b"%PDF-1.7\nduplicate authoritative binary\n%%EOF\n"
            for code in REQUIRED_CODES:
                payload = duplicate if code in {"GMP-SOP-001", "GMP-SOP-002"} else (
                    b"%PDF-1.7\n" + code.encode("ascii") + b"\n%%EOF\n"
                )
                (corpus_dir / f"{code}.pdf").write_bytes(payload)

            result = run_intake("--corpus-dir", str(corpus_dir))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "renamed duplicate files cannot represent two authoritative documents",
            "\n".join(json.loads(result.stdout)["errors"]),
        )

    def test_corrected_corpus_rejects_ai_draft_binary_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir) / "corpus"
            corpus_dir.mkdir()
            for code in REQUIRED_CODES:
                marker = b"\nAI_DRAFT_FOR_OWNER_REVIEW\n" if code == "GMP-SOP-001" else b"\n"
                (corpus_dir / f"{code}.pdf").write_bytes(
                    b"%PDF-1.7\n" + code.encode("ascii") + marker + b"%%EOF\n"
                )

            result = run_intake("--corpus-dir", str(corpus_dir))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "controlled draft marker 'AI_DRAFT_FOR_OWNER_REVIEW' is not accepted",
            "\n".join(json.loads(result.stdout)["errors"]),
        )


if __name__ == "__main__":
    unittest.main()
