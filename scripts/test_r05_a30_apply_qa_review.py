#!/usr/bin/env python3
"""Regression tests for R05-A30 QA Hoàn review acceptance recording."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from r05_a30_apply_qa_review import (
    DEFAULT_SOURCE_QUEUE_JSON,
    DOCUMENT_QUEUE_TYPE,
    DOCUMENT_REVIEW_DECISION,
    DOCUMENT_REVIEW_STATUS,
    OCR_PAGE_PENDING_DECISION,
    OCR_POLICY_APPROVED_STATUS,
    OCR_QUEUE_TYPE,
    REVIEWER,
    apply_review,
    write_outputs,
)


class R05A30ApplyQaReviewTest(unittest.TestCase):
    def test_real_a29_queue_accepts_twelve_document_reviews(self) -> None:
        pack = apply_review()

        self.assertEqual(
            pack["decision"],
            "LOCAL_PARTIAL_REVIEW_ACCEPTED_DOCUMENTS_ONLY_OCR_POLICY_APPROVED",
        )
        self.assertFalse(pack["errors"])
        self.assertEqual(pack["reviewer"]["name"], "Hoàn")
        self.assertEqual(pack["reviewer"]["role"], "QA")
        self.assertEqual(pack["reviewer"]["reviewed_at"], "2026-06-30T18:40:00+07:00")
        self.assertEqual(pack["remote_operations"]["supabase"], [])
        self.assertEqual(pack["remote_operations"]["n8n"], [])
        self.assertEqual(pack["remote_operations"]["git"], [])

        document_items = [
            item for item in pack["queue_items"] if item["queue_type"] == DOCUMENT_QUEUE_TYPE
        ]
        self.assertEqual(len(document_items), 12)
        self.assertEqual(pack["summary"]["document_review_items"], 12)
        self.assertEqual(pack["summary"]["document_accepted_count"], 12)
        for item in document_items:
            self.assertEqual(item["reviewer_name"], REVIEWER["name"])
            self.assertEqual(item["reviewer_role"], REVIEWER["role"])
            self.assertEqual(item["review_status"], DOCUMENT_REVIEW_STATUS)
            self.assertEqual(item["reviewer_decision"], DOCUMENT_REVIEW_DECISION)
            self.assertEqual(item["auto_approve"], "FALSE")
            self.assertEqual(item["ai_use_allowed"], "FALSE")
            self.assertEqual(item["remote_mutation_allowed"], "FALSE")
            self.assertEqual(
                item["production_retrieval"],
                "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS",
            )
            self.assertTrue(item["drive_web_view_link"].startswith("https://drive.google.com/file/d/"))

    def test_ocr_policy_is_approved_without_page_level_acceptance(self) -> None:
        pack = apply_review()
        ocr_items = [item for item in pack["queue_items"] if item["queue_type"] == OCR_QUEUE_TYPE]
        ocr_by_page = {item["page_number"]: item for item in ocr_items}

        self.assertEqual(set(ocr_by_page), {"1", "2", "3", "9", "17"})
        self.assertTrue(pack["summary"]["ocr_policy_approved_by_qa"])
        self.assertEqual(pack["summary"]["ocr_page_review_items"], 5)
        self.assertEqual(pack["summary"]["ocr_page_decision_count"], 0)
        self.assertEqual(pack["summary"]["ocr_page_pending_count"], 5)
        self.assertEqual(
            pack["summary"]["blk004_status_after_review"],
            "OPEN_PARTIAL_PROGRESS_DOCUMENTS_REVIEWED_OCR_PAGES_PENDING",
        )

        expected_status_by_page = {
            "1": "ENGINE_DISAGREEMENT_RETRY_REQUIRED",
            "2": "LOW_CONFIDENCE_DASHBOARD_APPROVAL_REQUIRED",
            "3": "MULTI_ENGINE_MATCH_PASS_PENDING_HUMAN_REVIEW",
            "9": "ENGINE_DISAGREEMENT_RETRY_REQUIRED",
            "17": "LOW_CONFIDENCE_DASHBOARD_APPROVAL_REQUIRED",
        }
        for page, expected_status in expected_status_by_page.items():
            item = ocr_by_page[page]
            self.assertEqual(item["multi_engine_policy_status"], expected_status)
            self.assertEqual(item["reviewer_name"], REVIEWER["name"])
            self.assertEqual(item["reviewer_role"], REVIEWER["role"])
            self.assertEqual(item["review_status"], OCR_POLICY_APPROVED_STATUS)
            self.assertEqual(item["reviewer_decision"], OCR_PAGE_PENDING_DECISION)
            self.assertNotEqual(item["reviewer_decision"], "ĐẠT")
            self.assertIn("Explicit per-page OCR decision was not supplied", item["reviewer_notes"])
            self.assertEqual(item["auto_approve"], "FALSE")
            self.assertEqual(item["ai_use_allowed"], "FALSE")
            self.assertEqual(item["remote_mutation_allowed"], "FALSE")

    def test_missing_source_queue_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.json"
            pack = apply_review(missing_path)

        self.assertEqual(pack["decision"], "FAIL_CLOSED_INPUT_INVALID")
        self.assertTrue(pack["errors"])
        self.assertFalse(pack["summary"]["ocr_policy_approved_by_qa"])
        self.assertEqual(pack["remote_operations"]["supabase"], [])
        self.assertEqual(pack["remote_operations"]["n8n"], [])
        self.assertEqual(pack["queue_items"], [])

    def test_source_queue_with_missing_ocr_page_fails_closed(self) -> None:
        source_payload = json.loads(DEFAULT_SOURCE_QUEUE_JSON.read_text(encoding="utf-8"))
        source_payload["queue_items"] = [
            item
            for item in source_payload["queue_items"]
            if not (item.get("queue_type") == OCR_QUEUE_TYPE and item.get("page_number") == "17")
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "queue.json"
            temp_path.write_text(json.dumps(source_payload, ensure_ascii=False), encoding="utf-8")
            pack = apply_review(temp_path)

        self.assertEqual(pack["decision"], "FAIL_CLOSED_INPUT_INVALID")
        self.assertTrue(any("OCR page review items" in error for error in pack["errors"]))
        self.assertEqual(pack["queue_items"], [])

    def test_write_outputs_creates_reviewed_queue_report_and_input_note(self) -> None:
        pack = apply_review()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = write_outputs(
                pack,
                queue_csv_path=root / "queue.csv",
                queue_json_path=root / "queue.json",
                report_json_path=root / "report.json",
                review_input_md_path=root / "review-input.md",
            )

            for path_name in ("queue.csv", "queue.json", "report.json", "review-input.md"):
                self.assertTrue((root / path_name).is_file(), path_name)
            queue_payload = json.loads((root / "queue.json").read_text(encoding="utf-8"))
            report_payload = json.loads((root / "report.json").read_text(encoding="utf-8"))
            review_note = (root / "review-input.md").read_text(encoding="utf-8")

        self.assertEqual(report["decision"], "LOCAL_PARTIAL_REVIEW_ACCEPTED_DOCUMENTS_ONLY_OCR_POLICY_APPROVED")
        self.assertEqual(queue_payload["summary"]["queue_item_count"], 17)
        self.assertEqual(report_payload["summary"]["document_accepted_count"], 12)
        self.assertIn("QA Hoàn", review_note)
        self.assertIn("Đạt cả", review_note)
        self.assertIn("A30 did not call Drive live", review_note)
        self.assertIn("all five OCR pages remain `CHƯA REVIEW`", review_note)


if __name__ == "__main__":
    unittest.main()
