from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from r05_a29_multi_engine_review_pack import (
    DEFAULT_CATALOG,
    DEFAULT_DOCUMENT_REVIEW_QUEUE,
    DEFAULT_OCR_REVIEW_QUEUE,
    build_pack,
    write_outputs,
)


class MultiEngineReviewPackTest(unittest.TestCase):
    def test_real_inputs_build_seventeen_fail_closed_queue_items(self):
        pack = build_pack()
        self.assertEqual(pack["decision"], "LOCAL_READY_REVIEW_DASHBOARD_QUEUE_CREATED")
        self.assertFalse(pack["errors"])
        self.assertEqual(pack["summary"]["queue_item_count"], 17)
        self.assertEqual(pack["summary"]["document_review_items"], 12)
        self.assertEqual(pack["summary"]["ocr_page_review_items"], 5)
        self.assertTrue(pack["summary"]["all_human_review_required"])
        self.assertTrue(pack["summary"]["all_auto_approve_false"])
        self.assertTrue(pack["summary"]["all_ai_use_allowed_false"])
        self.assertTrue(pack["summary"]["all_remote_mutation_false"])
        for item in pack["queue_items"]:
            self.assertEqual(item["review_status"], "PENDING_ACCOUNTABLE_HUMAN_REVIEW")
            self.assertEqual(item["reviewer_decision"], "PENDING")
            self.assertEqual(item["auto_approve"], "FALSE")
            self.assertEqual(item["ai_use_allowed"], "FALSE")
            self.assertEqual(item["remote_mutation_allowed"], "FALSE")

    def test_ocr_pages_are_classified_by_multi_engine_policy(self):
        pack = build_pack()
        ocr_by_page = {
            item["page_number"]: item
            for item in pack["queue_items"]
            if item["queue_type"] == "OCR_PAGE_REVIEW"
        }
        self.assertEqual(set(ocr_by_page), {"1", "2", "3", "9", "17"})
        self.assertEqual(
            ocr_by_page["3"]["multi_engine_policy_status"],
            "MULTI_ENGINE_MATCH_PASS_PENDING_HUMAN_REVIEW",
        )
        self.assertEqual(
            ocr_by_page["3"]["policy_required_machine_action"],
            "NO_RETRY_REQUIRED",
        )
        for page in ("1", "9"):
            self.assertEqual(
                ocr_by_page[page]["multi_engine_policy_status"],
                "ENGINE_DISAGREEMENT_RETRY_REQUIRED",
            )
            self.assertEqual(
                ocr_by_page[page]["policy_required_dashboard_action"],
                "ESCALATE_IF_RETRY_STILL_DIFFERS",
            )
        for page in ("2", "17"):
            self.assertEqual(
                ocr_by_page[page]["multi_engine_policy_status"],
                "LOW_CONFIDENCE_DASHBOARD_APPROVAL_REQUIRED",
            )
            self.assertEqual(
                ocr_by_page[page]["policy_required_dashboard_action"],
                "ACCOUNTABLE_HUMAN_APPROVAL_REQUIRED",
            )

    def test_drive_catalog_identity_is_preserved_in_document_queue(self):
        pack = build_pack()
        document_items = [
            item
            for item in pack["queue_items"]
            if item["queue_type"] == "DOCUMENT_REFERENCE_REVIEW"
        ]
        self.assertEqual(len({item["document_code"] for item in document_items}), 12)
        self.assertEqual(len({item["drive_file_id"] for item in document_items}), 12)
        self.assertEqual(len({item["source_sha256"] for item in document_items}), 12)
        self.assertTrue(all(item["document_code"].startswith("REF-") for item in document_items))
        self.assertTrue(all(item["drive_web_view_link"].startswith("https://drive.google.com/file/d/") for item in document_items))

    def test_missing_ocr_page_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "ocr.csv"
            with DEFAULT_OCR_REVIEW_QUEUE.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            rows = rows[:-1]
            with temp_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            pack = build_pack(ocr_review_queue_path=temp_path)
        self.assertEqual(pack["decision"], "FAIL_CLOSED_INPUT_INVALID")
        self.assertTrue(any("OCR review queue" in error for error in pack["errors"]))

    def test_write_outputs_creates_dashboard_files_and_reviewer_template(self):
        pack = build_pack(
            catalog_path=DEFAULT_CATALOG,
            document_review_queue_path=DEFAULT_DOCUMENT_REVIEW_QUEUE,
            ocr_review_queue_path=DEFAULT_OCR_REVIEW_QUEUE,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = write_outputs(
                pack,
                queue_csv_path=root / "queue.csv",
                queue_json_path=root / "queue.json",
                policy_json_path=root / "policy.json",
                review_template_path=root / "review.md",
                report_json_path=root / "report.json",
            )
            self.assertEqual(report["decision"], "LOCAL_READY_REVIEW_DASHBOARD_QUEUE_CREATED")
            for path_name in ("queue.csv", "queue.json", "policy.json", "review.md", "report.json"):
                self.assertTrue((root / path_name).is_file())
            queue_payload = json.loads((root / "queue.json").read_text(encoding="utf-8"))
            self.assertEqual(queue_payload["summary"]["queue_item_count"], 17)
            self.assertIn("Review 12 tài liệu", (root / "review.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
