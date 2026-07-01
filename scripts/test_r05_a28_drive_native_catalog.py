from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from r05_a28_drive_native_catalog import (
    DEFAULT_CORPUS,
    DEFAULT_INVENTORY,
    DEFAULT_REVIEW_QUEUE,
    build_report,
)


class DriveNativeCatalogTest(unittest.TestCase):
    def test_real_evidence_builds_twelve_fail_closed_catalog_records(self):
        report = build_report()
        self.assertEqual(
            report["decision"],
            "LOCAL_READY_REMOTE_APPROVAL_AND_HUMAN_REVIEW_REQUIRED",
        )
        self.assertEqual(report["catalog_record_count"], 12)
        self.assertEqual(report["retirement_record_count"], 10)
        self.assertFalse(report["errors"])
        self.assertEqual(
            len({row["drive_file_id"] for row in report["catalog_records"]}), 12
        )
        self.assertEqual(
            len({row["binary_sha256"] for row in report["catalog_records"]}), 12
        )
        for row in report["catalog_records"]:
            self.assertTrue(row["document_code"].startswith("REF-"))
            self.assertFalse(row["approved_for_ai_use"])
            self.assertEqual(row["content_review_status"], "PENDING_ACCOUNTABLE_HUMAN_REVIEW")
            self.assertEqual(row["production_retrieval"], "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS")

    def test_retirement_is_reversible_and_never_hard_deletes(self):
        report = build_report()
        plan = report["retirement_plan"]
        self.assertEqual([row["document_code"] for row in plan], [f"GMP-SOP-{i:03d}" for i in range(1, 11)])
        for row in plan:
            self.assertEqual(row["target_document_status"], "archived")
            self.assertFalse(row["target_approved_for_ai_use"])
            self.assertFalse(row["hard_delete"])
            self.assertIn("PRESERVE", row["current_version_action"])

    def test_hash_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "queue.csv"
            with DEFAULT_REVIEW_QUEUE.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["source_sha256"] = "0" * 64
            with queue_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            report = build_report(
                inventory_path=DEFAULT_INVENTORY,
                review_queue_path=queue_path,
                corpus_dir=DEFAULT_CORPUS,
            )
        self.assertEqual(report["decision"], "FAIL_CLOSED_CATALOG_EVIDENCE_MISMATCH")
        self.assertTrue(any("SHA-256" in error for error in report["errors"]))

    def test_missing_input_fails_closed_without_inferred_records(self):
        report = build_report(inventory_path=Path("/definitely/missing.csv"))
        self.assertEqual(report["decision"], "FAIL_CLOSED_MISSING_INPUT")
        self.assertEqual(report["catalog_records"], [])


if __name__ == "__main__":
    unittest.main()
