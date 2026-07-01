#!/usr/bin/env python3
"""Regression assertions for R05-A08 page-7 table/figure fail-closed benchmark."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "docs/checkpoints/search-upgrade/r05-a08-page7-engine-summary.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A08-page7-table-figure-benchmark.md"
BENCHMARK_SCRIPT = ROOT / "scripts/r05_a08_page7_benchmark.py"
DOCLING_SCRIPT = ROOT / "scripts/r05_a08_docling_table.py"
PADDLE_SCRIPT = ROOT / "scripts/r05_a08_paddle_table.py"


class R05A08Page7BenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")

    def test_source_and_page_identity(self) -> None:
        self.assertEqual(self.summary["action"], "R05-A08")
        self.assertEqual(self.summary["source"]["drive_file_id"], "1PqmkUQUXLL6N3CgzEv-_xOPGH10n_4cb")
        self.assertEqual(self.summary["source"]["bytes"], 1093396)
        self.assertEqual(
            self.summary["source"]["sha256"],
            "9de58a48669e4f00c6b4e284cd435a5000e03e6ee4b7c3c37121a1289ff6a828",
        )
        self.assertEqual(self.summary["page"]["number"], 7)
        self.assertEqual(self.summary["page"]["content"], "figure_plus_formal_specification_table")

    def test_table_engines_disagree_and_fail_closed(self) -> None:
        extractors = self.summary["table_extractors"]
        self.assertEqual(extractors["pdfplumber_native_line"]["shape"], [14, 4])
        self.assertEqual(extractors["camelot_lattice"]["shape"], [14, 4])
        self.assertTrue(extractors["camelot_lattice"]["matches_pdfplumber_native_line"])
        self.assertEqual(extractors["pdfplumber_text_strategy"]["shape"], [17, 6])
        self.assertEqual(extractors["camelot_stream"]["shape"], [17, 2])
        self.assertEqual(extractors["docling_tableformer_pdf"]["shape"], [13, 4])
        self.assertEqual(extractors["paddleocr_pp_tablemagic_300dpi"]["shape"], [9, 4])
        self.assertEqual(extractors["paddleocr_pp_tablemagic_400dpi"]["shape"], [8, 4])
        decision = self.summary["decision"]
        self.assertFalse(decision["structural_agreement"])
        self.assertTrue(decision["retry_400dpi_completed"])
        self.assertFalse(decision["auto_save_allowed"])
        self.assertFalse(decision["production_import_allowed"])

    def test_visual_evidence_has_crop_hashes(self) -> None:
        table = self.summary["visual_evidence"]["table_crop"]
        figure = self.summary["visual_evidence"]["figure_crop"]
        self.assertEqual(table["bbox_px_300dpi"], [301, 1836, 2249, 2829])
        self.assertEqual(figure["bbox_px_300dpi"], [611, 537, 2003, 1669])
        self.assertRegex(table["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(figure["sha256"], r"^[0-9a-f]{64}$")

    def test_checkpoint_records_no_live_mutation_and_workflow_p_contract(self) -> None:
        self.assertIn("DONE_FAIL_CLOSED_REQUIRES_HUMAN_QA", self.checkpoint)
        self.assertIn("Workflow-P upgrade plan", self.checkpoint)
        self.assertIn("No Supabase write/import/chunk/embedding", self.checkpoint)
        self.assertIn("No n8n create/update/execute/publish/archive", self.checkpoint)
        self.assertIn("No Git remote action", self.checkpoint)

    def test_scripts_keep_scope_local_only(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [BENCHMARK_SCRIPT, DOCLING_SCRIPT, PADDLE_SCRIPT]
        ).lower()
        forbidden = [
            "create_workflow",
            "update_workflow",
            "publish_workflow",
            "execute_workflow",
            "supabase db push",
            "git push",
        ]
        for token in forbidden:
            self.assertNotIn(token, combined)


if __name__ == "__main__":
    unittest.main()
