#!/usr/bin/env python3
"""Tests for R05-A26 bounded local Vision OCR evidence."""

from __future__ import annotations

import importlib.util
import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a26_bounded_vision_ocr.py"
REPORT = ROOT / "work/r05_a26_bounded_vision_ocr_report.json"
CORPUS_QUEUE = ROOT / "work/r05_a26_blk004_corpus_review_queue.csv"
OCR_QUEUE = ROOT / "work/r05_a26_ocr_page_review_queue.csv"

spec = importlib.util.spec_from_file_location("r05_a26_bounded_vision_ocr", SCRIPT)
assert spec and spec.loader
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)


class R05A26BoundedVisionOcrTest(unittest.TestCase):
    def test_compare_passes_detects_numeric_disagreement(self) -> None:
        left = {
            "pass_id": "left",
            "normalized_text": "temperature 2 c to 8 c",
            "word_count": 6,
            "critical_tokens": ["2 c", "8 c"],
        }
        right = {
            "pass_id": "right",
            "normalized_text": "temperature 2 c to 80 c",
            "word_count": 6,
            "critical_tokens": ["2 c", "80 c"],
        }

        comparison = operator.compare_passes(left, right)

        self.assertFalse(comparison["critical_tokens_match"])
        self.assertFalse(comparison["agreement_pass"])
        self.assertEqual(comparison["critical_tokens_only_left"], ["8 c"])
        self.assertEqual(comparison["critical_tokens_only_right"], ["80 c"])

    def test_parse_pages_deduplicates_without_sorting(self) -> None:
        self.assertEqual(operator.parse_pages("1,2,2,9,17"), (1, 2, 9, 17))

    def test_retained_report_is_bounded_and_never_auto_approves(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertTrue(report["execution_ok"])
        self.assertEqual(
            report["decision"],
            "BOUNDED_OCR_EVIDENCE_RECORDED_HUMAN_REVIEW_REQUIRED",
        )
        self.assertEqual(report["bounded_scope"]["selected_pages"], [1, 2, 3, 9, 17])
        self.assertFalse(report["bounded_scope"]["full_document_ocr"])
        self.assertEqual(report["summary"]["page_records"], 5)
        self.assertEqual(report["summary"]["passes_executed"], 15)
        self.assertEqual(report["summary"]["auto_approved_pages"], 0)
        self.assertTrue(report["summary"]["human_review_required"])
        self.assertEqual(report["corpus_evidence_summary"]["text_layer_parse_ready_records"], 11)
        self.assertEqual(report["corpus_evidence_summary"]["bounded_ocr_evidence_records"], 1)
        self.assertEqual(report["corpus_evidence_summary"]["technical_extraction_covered_records"], 12)
        self.assertTrue(report["corpus_evidence_summary"]["technical_extraction_evidence_complete"])
        self.assertFalse(report["corpus_evidence_summary"]["mapping_complete"])
        self.assertTrue(report["source"]["sha256_matches_a25"])
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        for page in report["pages"]:
            self.assertFalse(page["auto_approve"])
            for ocr_pass in page["passes"]:
                self.assertNotIn("text", ocr_pass)
                self.assertNotIn("lines", ocr_pass)
                self.assertFalse(ocr_pass["full_text_retained"])

    def test_review_queues_are_complete_and_pending(self) -> None:
        with CORPUS_QUEUE.open(encoding="utf-8", newline="") as handle:
            corpus_rows = list(csv.DictReader(handle))
        with OCR_QUEUE.open(encoding="utf-8", newline="") as handle:
            ocr_rows = list(csv.DictReader(handle))

        self.assertEqual(len(corpus_rows), 12)
        self.assertEqual(len(ocr_rows), 5)
        self.assertEqual(
            sum(row["extraction_path"] == "BOUNDED_APPLE_VISION_OCR" for row in corpus_rows),
            1,
        )
        for row in [*corpus_rows, *ocr_rows]:
            self.assertEqual(row["review_status"], "PENDING_ACCOUNTABLE_HUMAN_REVIEW")
            self.assertEqual(row["reviewer_decision"], "PENDING")
            self.assertEqual(row["auto_approve"], "FALSE")


if __name__ == "__main__":
    unittest.main()
