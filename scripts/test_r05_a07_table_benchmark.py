#!/usr/bin/env python3
"""Regression assertions for R05-A07 fail-closed table benchmark."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_SOURCE = ROOT / "work/r05_a07_table_sample_export_workflow.js"
RESULT = ROOT / "docs/checkpoints/search-upgrade/r05-a07-three-engine-table-result.json"
DOCLING_300 = ROOT / "work/r05_a07_docling.json"
DOCLING_400 = ROOT / "work/r05_a07_docling_400.json"
PADDLE_300 = ROOT / "work/r05_a07_paddle.json"
PADDLE_400 = ROOT / "work/r05_a07_paddle_400.json"
NATIVE = ROOT / "work/r05_a07_pdfplumber.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A07-three-engine-table-benchmark.md"


class R05A07TableBenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow_source = WORKFLOW_SOURCE.read_text(encoding="utf-8")
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.docling_300 = json.loads(DOCLING_300.read_text(encoding="utf-8"))
        cls.docling_400 = json.loads(DOCLING_400.read_text(encoding="utf-8"))
        cls.paddle_300 = json.loads(PADDLE_300.read_text(encoding="utf-8"))
        cls.paddle_400 = json.loads(PADDLE_400.read_text(encoding="utf-8"))
        cls.native = json.loads(NATIVE.read_text(encoding="utf-8"))
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")

    def test_workflow_source_is_exact_probe_scope(self) -> None:
        self.assertIn("TKTL R05-A07 Table Sample Export Probe", self.workflow_source)
        self.assertIn("1G0fencQsGt0c5HtUJP5WER-kJ5it1S3m", self.workflow_source)
        self.assertIn("ISO 14644-6 2007 Cleanrooms_and.pdf", self.workflow_source)
        self.assertIn("403205", self.workflow_source)
        self.assertIn("googleDrive", self.workflow_source)
        forbidden = ["postgres", "supabase", "publish", "unpublish", "archiveWorkflow"]
        lowered = self.workflow_source.lower()
        for token in forbidden:
            self.assertNotIn(token.lower(), lowered)

    def test_result_denies_auto_save(self) -> None:
        decision = self.result["decision"]
        self.assertFalse(decision["auto_save_allowed"])
        self.assertFalse(decision["structural_agreement"])
        self.assertTrue(decision["retry_400dpi_completed"])
        self.assertFalse(decision["retry_resolved_disagreement"])
        self.assertEqual(self.result["candidate_type"], "borderless_bilingual_aligned_glossary")
        self.assertEqual(self.result["page"], 10)

    def test_extractor_outputs_match_fail_closed_disagreement(self) -> None:
        self.assertEqual(self.docling_300["table_count"], 0)
        self.assertEqual(self.docling_400["table_count"], 0)
        self.assertEqual(self.paddle_300["table_count"], 0)
        self.assertEqual(self.paddle_400["table_count"], 0)
        self.assertEqual(self.native["formal_line_table_count"], 0)
        self.assertEqual(self.native["text_strategy_table_count"], 1)
        self.assertEqual(self.native["text_strategy_shapes"], [[57, 7]])
        self.assertEqual(self.native["semantic_rows"], 6)
        self.assertEqual(self.native["semantic_columns"], 2)
        self.assertTrue(self.native["anchor_pairs_match"])

    def test_comparison_json_summarizes_all_engines(self) -> None:
        engines = self.result["engines"]
        self.assertEqual(engines["docling"]["table_count"], 0)
        self.assertEqual(engines["docling_400dpi"]["table_count"], 0)
        self.assertEqual(engines["paddle"]["table_count"], 0)
        self.assertEqual(engines["paddle_400dpi"]["table_count"], 0)
        self.assertEqual(engines["native"]["semantic_shape"], [6, 2])
        self.assertTrue(engines["native"]["anchor_pairs_match"])

    def test_checkpoint_records_scope_and_blk004_status(self) -> None:
        self.assertIn("BLK-004 remains OPEN", self.checkpoint)
        self.assertIn("does not write Supabase", self.checkpoint)
        self.assertIn("does not publish/unpublish/archive", self.checkpoint)
        self.assertIn("CODEX SELF-REVIEW", self.checkpoint)


if __name__ == "__main__":
    unittest.main()
