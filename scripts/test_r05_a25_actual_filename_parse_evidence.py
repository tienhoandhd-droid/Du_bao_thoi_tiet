#!/usr/bin/env python3
"""Tests for the R05-A25 actual-filename parse evidence gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a25_actual_filename_parse_evidence.py"
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_MAPPING_TEMPLATE = ROOT / "work/r05_a25_actual_filename_mapping_required.csv"
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


def create_pdf(path: Path, text: str) -> None:
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        raise unittest.SkipTest(f"reportlab unavailable: {exc!r}")

    c = canvas.Canvas(str(path), pagesize=A4)
    text_object = c.beginText(50, 790)
    for line in text.splitlines():
        text_object.textLine(line)
    c.drawText(text_object)
    c.showPage()
    c.save()


def actual_file_names() -> list[str]:
    return [f"Owner Source {idx:02d} Actual Title.pdf" for idx in range(1, 13)]


def populate_corpus(corpus_dir: Path, low_text_index: int | None = None) -> list[str]:
    names = actual_file_names()
    for idx, name in enumerate(names, start=1):
        word_values = [f"word{idx}_{position}" for position in range(140)]
        wrapped = "\n".join(
            " ".join(word_values[start:start + 10])
            for start in range(0, len(word_values), 10)
        )
        text = "short" if idx == low_text_index else f"{name}\n{wrapped}"
        create_pdf(corpus_dir / name, text)
    return names


def write_mapping(path: Path, names: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["document_code", "file_name", "status", "mapping_notes"],
        )
        writer.writeheader()
        for code, name in zip(REQUIRED_CODES, names, strict=True):
            writer.writerow(
                {
                    "document_code": code,
                    "file_name": name,
                    "status": "OWNER_CONFIRMED_FILENAME_MAPPING",
                    "mapping_notes": "unit-test owner mapping",
                }
            )


class R05A25ActualFilenameParseEvidenceTest(unittest.TestCase):
    def test_actual_filename_corpus_records_parse_evidence_but_requires_owner_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus = base / "actual"
            corpus.mkdir()
            output = base / "report.json"
            template = base / "mapping_required.csv"
            populate_corpus(corpus)

            result = run_operator(
                "--corpus-dir",
                str(corpus),
                "--mapping-template",
                str(template),
                "--output",
                str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            with template.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "LOCAL_PARSE_EVIDENCE_READY_MAPPING_REQUIRED")
        self.assertEqual(report["summary"]["pdf_file_count"], 12)
        self.assertEqual(report["summary"]["parse_ready_records"], 12)
        self.assertFalse(report["summary"]["mapping_complete"])
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row["document_code"] == "REQUIRED_OWNER_MAPPING" for row in rows))
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})

    def test_complete_actual_filename_mapping_reaches_review_ready_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus = base / "actual"
            corpus.mkdir()
            output = base / "report.json"
            mapping = base / "mapping.csv"
            names = populate_corpus(corpus)
            write_mapping(mapping, names)

            result = run_operator(
                "--corpus-dir",
                str(corpus),
                "--mapping-csv",
                str(mapping),
                "--output",
                str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report["ok"])
        self.assertEqual(report["decision"], "LOCAL_PARSE_EVIDENCE_READY_REVIEW_REQUIRED")
        self.assertTrue(report["summary"]["mapping_complete"])
        self.assertEqual(report["summary"]["mapped_records"], 12)
        self.assertEqual({record["mapped_document_code"] for record in report["records"]}, set(REQUIRED_CODES))

    def test_low_text_layer_requires_parse_or_ocr_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus = base / "actual"
            corpus.mkdir()
            output = base / "report.json"
            populate_corpus(corpus, low_text_index=3)

            result = run_operator(
                "--corpus-dir",
                str(corpus),
                "--output",
                str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["decision"], "FAIL_CLOSED_PARSE_REVIEW_REQUIRED")
        self.assertGreaterEqual(report["summary"]["parse_review_required_records"], 1)
        self.assertIn("require parse/OCR review", "\n".join(report["errors"]))

    def test_retained_mapping_template_matches_current_actual_corpus_filenames(self) -> None:
        corpus_names = sorted(path.name for path in DEFAULT_CORPUS.glob("*.pdf"))
        with DEFAULT_MAPPING_TEMPLATE.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(corpus_names), 12)
        self.assertEqual(len(rows), 12)
        self.assertEqual(sorted(row["file_name"] for row in rows), corpus_names)
        self.assertTrue(all(row["document_code"] == "REQUIRED_OWNER_MAPPING" for row in rows))
        self.assertTrue(all(row["status"] == "PENDING_OWNER_CONFIRMATION" for row in rows))


if __name__ == "__main__":
    unittest.main()
