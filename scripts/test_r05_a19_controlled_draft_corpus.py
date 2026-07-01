#!/usr/bin/env python3
"""Tests for the R05-A19 controlled draft corpus package."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment-dependent optional fixture
    A4 = None
    canvas = None
    REPORTLAB_IMPORT_ERROR = exc


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/r05_a19_build_controlled_draft_corpus.py"
INTAKE = ROOT / "scripts/r05_authoritative_corpus_intake.py"
REPORT = ROOT / "work/r05_a19_controlled_draft_corpus_hash_parse_report.json"
MANIFEST = ROOT / "work/r05_a19_controlled_draft_corpus_manifest.csv"
REVIEW_QUEUE = ROOT / "work/r05_a19_owner_review_queue.csv"


def write_fake_who_pdf(path: Path) -> None:
    if canvas is None or A4 is None:  # pragma: no cover - guarded by skip in tests
        raise RuntimeError(f"reportlab unavailable: {REPORTLAB_IMPORT_ERROR!r}")
    doc = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    doc.setTitle("WHO TRS 996 Test Source")
    doc.setAuthor("R05-A19 test fixture")
    doc.drawString(72, 760, "WHO Technical Report Series 996")
    doc.drawString(72, 735, "Annex 5 Data integrity guidance")
    doc.showPage()
    doc.drawString(72, 760, "WHO TRS 996 official reference test page")
    doc.drawString(72, 735, "Data integrity, ALCOA, audit trail and review evidence.")
    doc.save()


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class R05A19ControlledDraftCorpusTest(unittest.TestCase):
    @unittest.skipIf(REPORTLAB_IMPORT_ERROR is not None, f"reportlab unavailable: {REPORTLAB_IMPORT_ERROR!r}")
    def test_generator_builds_review_package_but_keeps_production_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            who_source = base / "WHO-TRS-996-source.pdf"
            output_dir = base / "draft-corpus"
            manifest = base / "manifest.csv"
            report_path = base / "report.json"
            review_queue = base / "review.csv"
            write_fake_who_pdf(who_source)

            result = run_command(
                str(GENERATOR),
                "--who-trs-996-source",
                str(who_source),
                "--output-dir",
                str(output_dir),
                "--manifest",
                str(manifest),
                "--report",
                str(report_path),
                "--review-queue",
                str(review_queue),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))

            pdfs = sorted(output_dir.glob("*.pdf"))
            self.assertEqual(len(pdfs), 12)
            self.assertEqual(report["decision"], "READY_FOR_OWNER_REVIEW_NOT_PRODUCTION")
            self.assertEqual(report["document_count"], 12)
            self.assertEqual(report["draft_document_count"], 11)
            self.assertEqual(report["official_reference_count"], 1)
            self.assertEqual(report["authoritative_confirmed_count"], 0)
            self.assertFalse(report["production_import_allowed"])
            self.assertFalse(report["retrieval_enablement_allowed"])
            self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
            self.assertEqual(report["aggregate"]["pdf_signature_pass"], 12)
            self.assertEqual(report["aggregate"]["identity_pass"], 12)
            self.assertEqual(report["aggregate"]["unique_binary_sha256"], 12)

            lane = json.loads((output_dir / ".r05_draft_lane.json").read_text(encoding="utf-8"))
            self.assertFalse(lane["authoritative_eligible"])
            self.assertFalse(lane["production_import_allowed"])

            draft_records = [
                record for record in report["records"]
                if record["artifact_status"] == "AI_DRAFT_FOR_OWNER_REVIEW"
            ]
            self.assertEqual(len(draft_records), 11)
            self.assertTrue(all(record["draft_marker_present"] for record in draft_records))
            self.assertTrue(all(record["authoritative_confirmed"] == "false" for record in report["records"]))

            with manifest.open(encoding="utf-8", newline="") as handle:
                manifest_rows = list(csv.DictReader(handle))
            with review_queue.open(encoding="utf-8", newline="") as handle:
                review_rows = list(csv.DictReader(handle))
            self.assertEqual(len(manifest_rows), 12)
            self.assertEqual(len(review_rows), 12)
            self.assertTrue(
                all(row["promotion_decision"] == "DENY_UNTIL_ALL_REQUIRED_REVIEWS_PASS" for row in review_rows)
            )

            intake = run_command(str(INTAKE), "--corpus-dir", str(output_dir))

        self.assertNotEqual(intake.returncode, 0)
        intake_report = json.loads(intake.stdout)
        self.assertEqual(intake_report["decision"], "FAIL_CLOSED")
        self.assertIn("controlled draft marker", "\n".join(intake_report["errors"]))

    def test_retained_artifacts_are_review_only_and_match_blocker_contract(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        with MANIFEST.open(encoding="utf-8", newline="") as handle:
            manifest_rows = list(csv.DictReader(handle))
        with REVIEW_QUEUE.open(encoding="utf-8", newline="") as handle:
            review_rows = list(csv.DictReader(handle))

        self.assertEqual(report["rhythm"], "R05-A19")
        self.assertEqual(report["decision"], "READY_FOR_OWNER_REVIEW_NOT_PRODUCTION")
        self.assertEqual(report["document_count"], 12)
        self.assertEqual(len(manifest_rows), 12)
        self.assertEqual(len(review_rows), 12)
        self.assertEqual(report["authoritative_confirmed_count"], 0)
        self.assertFalse(report["production_import_allowed"])
        self.assertFalse(report["retrieval_enablement_allowed"])
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertTrue(all(row["authoritative_confirmed"] == "false" for row in manifest_rows))
        self.assertTrue(all(row["technical_sme_decision"] == "PENDING" for row in review_rows))
        self.assertTrue(all(value.startswith("OPEN") for value in report["blockers"].values()))


if __name__ == "__main__":
    unittest.main()
