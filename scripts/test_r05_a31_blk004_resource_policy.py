#!/usr/bin/env python3
"""Regression tests for R05-A31 resource-aware BLK-004 closure policy."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from r05_a31_blk004_resource_policy import (
    DEFAULT_A30_QUEUE_JSON,
    SOURCE_QUEUE_TYPE_DOC,
    SOURCE_QUEUE_TYPE_OCR,
    build_closure,
    write_outputs,
)


class R05A31Blk004ResourcePolicyTest(unittest.TestCase):
    def test_real_a30_queue_closes_blk004_without_claiming_100_percent(self) -> None:
        closure = build_closure()

        self.assertEqual(
            closure["decision"],
            "BLK004_CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED_SOURCE_ONLY",
        )
        self.assertFalse(closure["errors"])
        self.assertEqual(
            closure["summary"]["blk004_status_after_a31"],
            "CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED",
        )
        self.assertEqual(closure["summary"]["document_items"], 12)
        self.assertEqual(closure["summary"]["document_pass_count"], 12)
        self.assertEqual(closure["summary"]["ocr_items"], 5)
        self.assertEqual(closure["summary"]["ocr_closed_for_blk004_count"], 5)
        self.assertEqual(closure["summary"]["open_p0_after_blk004_closure"], ["BLK-003", "BLK-005", "BLK-006", "BLK-007"])
        self.assertTrue(closure["summary"]["future_upgrade_required"])
        self.assertTrue(closure["summary"]["no_100_percent_claim"])
        self.assertFalse(closure["summary"]["production_ai_use_allowed"])
        self.assertEqual(closure["remote_operations"], {"drive": [], "git": [], "n8n": [], "supabase": []})

    def test_ocr_pages_are_classified_by_resource_policy(self) -> None:
        closure = build_closure()
        ocr_items = {
            item["page_number"]: item
            for item in closure["closure_items"]
            if item["queue_type"] == SOURCE_QUEUE_TYPE_OCR
        }

        self.assertEqual(set(ocr_items), {"1", "2", "3", "9", "17"})
        self.assertEqual(ocr_items["3"]["blk004_disposition"], "PASS_MULTI_ENGINE_MATCH")
        self.assertEqual(ocr_items["3"]["al_note_required"], "FALSE")
        for page in ("1", "9"):
            self.assertEqual(ocr_items[page]["blk004_disposition"], "PASS_WITH_VARIANCE_AL_NOTE")
            self.assertEqual(ocr_items[page]["al_note_required"], "TRUE")
            self.assertEqual(ocr_items[page]["production_ai_use_allowed"], "FALSE")
        for page in ("2", "17"):
            self.assertEqual(ocr_items[page]["blk004_disposition"], "PASS_WITH_LOW_CONFIDENCE_AL_NOTE")
            self.assertEqual(ocr_items[page]["al_note_required"], "TRUE")
            self.assertEqual(ocr_items[page]["production_ai_use_allowed"], "FALSE")

        backlog_pages = {item["page_number"] for item in closure["al_backlog"]}
        self.assertEqual(backlog_pages, {"1", "2", "9", "17"})
        self.assertEqual(closure["summary"]["al_backlog_count"], 4)

    def test_document_items_remain_qa_review_passes(self) -> None:
        closure = build_closure()
        docs = [
            item
            for item in closure["closure_items"]
            if item["queue_type"] == SOURCE_QUEUE_TYPE_DOC
        ]

        self.assertEqual(len(docs), 12)
        for item in docs:
            self.assertEqual(item["source_review_status"], "ACCOUNTABLE_HUMAN_REVIEWED")
            self.assertEqual(item["source_reviewer_decision"], "ĐẠT")
            self.assertEqual(item["blk004_disposition"], "PASS_QA_DOCUMENT_REVIEW_ACCEPTED")
            self.assertEqual(item["blk004_closure_accepted"], "TRUE")
            self.assertEqual(item["al_note_required"], "FALSE")
            self.assertEqual(item["production_ai_use_allowed"], "FALSE")

    def test_missing_a30_queue_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.json"
            closure = build_closure(missing)

        self.assertEqual(closure["decision"], "FAIL_CLOSED_INPUT_INVALID")
        self.assertTrue(closure["errors"])
        self.assertEqual(
            closure["summary"]["blk004_status_after_a31"],
            "OPEN_FAIL_CLOSED_INVALID_INPUT",
        )
        self.assertIn("BLK-004", closure["summary"]["open_p0_after_blk004_closure"])

    def test_unaccepted_document_fails_closed(self) -> None:
        payload = json.loads(DEFAULT_A30_QUEUE_JSON.read_text(encoding="utf-8"))
        for item in payload["queue_items"]:
            if item["queue_type"] == SOURCE_QUEUE_TYPE_DOC:
                item["reviewer_decision"] = "CHƯA REVIEW"
                break

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "queue.json"
            temp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            closure = build_closure(temp_path)

        self.assertEqual(closure["decision"], "FAIL_CLOSED_INPUT_INVALID")
        self.assertTrue(any("reviewer_decision=ĐẠT" in error for error in closure["errors"]))

    def test_write_outputs_creates_policy_queue_backlog_and_report(self) -> None:
        closure = build_closure()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = write_outputs(
                closure,
                policy_json_path=root / "policy.json",
                closure_queue_json_path=root / "queue.json",
                closure_queue_csv_path=root / "queue.csv",
                al_backlog_csv_path=root / "al.csv",
                report_json_path=root / "report.json",
            )

            for name in ("policy.json", "queue.json", "queue.csv", "al.csv", "report.json"):
                self.assertTrue((root / name).is_file(), name)
            policy = json.loads((root / "policy.json").read_text(encoding="utf-8"))
            queue = json.loads((root / "queue.json").read_text(encoding="utf-8"))
            retained_report = json.loads((root / "report.json").read_text(encoding="utf-8"))

        self.assertEqual(report["decision"], "BLK004_CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED_SOURCE_ONLY")
        self.assertEqual(policy["policy_name"], "BLK004_RESOURCE_AWARE_MULTI_ENGINE_POLICY")
        self.assertEqual(queue["summary"]["al_backlog_count"], 4)
        self.assertEqual(retained_report["summary"]["blk004_status_after_a31"], "CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED")


if __name__ == "__main__":
    unittest.main()
