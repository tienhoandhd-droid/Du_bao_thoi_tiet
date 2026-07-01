#!/usr/bin/env python3
"""Static safety assertions for the source-only multimodal ingest contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "n8n/workflow-contracts/TKTL-R07-multimodal-ingest-validation.contract.json"
RESULT = ROOT / "docs/checkpoints/search-upgrade/r05-a06-three-engine-ocr-result.json"


class MultimodalIngestContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_source_only_and_fail_closed(self) -> None:
        self.assertEqual(self.contract["live_status"], "SOURCE_ONLY_NOT_DEPLOYED")
        self.assertEqual(self.contract["production_write_default"], "DENY")
        self.assertFalse(self.contract["on_missing_or_failed_assertion"]["production_write"])
        self.assertEqual(self.contract["on_missing_or_failed_assertion"]["state"], "QUARANTINED")

    def test_three_engines_and_critical_fields(self) -> None:
        self.assertGreaterEqual(self.contract["required_ocr_engines"], 3)
        critical = set(self.contract["critical_fields"])
        self.assertTrue({"number", "unit", "table_cell", "diagram_label"}.issubset(critical))

    def test_human_qa_is_mandatory(self) -> None:
        assertions = set(self.contract["promotion_assertions"])
        self.assertIn("human_qa_approved_for_gmp_critical_content", assertions)
        self.assertIn("source_crops_hash_verified", assertions)
        self.assertIn("current_document_version", assertions)
        self.assertIn("approved_for_ai_use", assertions)

    def test_benchmark_denies_auto_save(self) -> None:
        self.assertFalse(self.result["groundTruthAvailable"])
        self.assertFalse(self.result["decision"]["autoSaveAllowed"])
        self.assertEqual(set(self.result["decision"]["reviewPages"]), {1, 9, 18})
        self.assertTrue(all(page["requiresReview"] for page in self.result["pages"].values()))


if __name__ == "__main__":
    unittest.main()
