#!/usr/bin/env python3
"""Static assertions for R05-A09 Workflow P staging/review contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "n8n/workflow-contracts/TKTL-Workflow-P-staging-review.contract.json"
R05_A08_SUMMARY = ROOT / "docs/checkpoints/search-upgrade/r05-a08-page7-engine-summary.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A09-workflow-p-staging-review-contract.md"


class R05A09WorkflowPContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.summary = json.loads(R05_A08_SUMMARY.read_text(encoding="utf-8"))
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")

    def test_source_only_and_tktl_scope(self) -> None:
        self.assertEqual(self.contract["action"], "R05-A09")
        self.assertEqual(self.contract["project_ref"], "bdttccztjtrcaztjgkot")
        self.assertEqual(self.contract["workflow_scope"], "TKTL_ONLY")
        self.assertEqual(self.contract["live_status"], "SOURCE_ONLY_NOT_DEPLOYED")
        self.assertEqual(self.contract["production_write_default"], "DENY")
        self.assertTrue(self.contract["approval_required_before_live"])

    def test_r05_a08_hashes_are_preserved(self) -> None:
        evidence = self.contract["source_evidence"]
        self.assertEqual(evidence["source_pdf_sha256"], self.summary["source"]["sha256"])
        self.assertEqual(evidence["page_number"], self.summary["page"]["number"])
        self.assertEqual(evidence["page_render_300dpi_sha256"], self.summary["page"]["render_300dpi_sha256"])
        self.assertEqual(evidence["page_render_400dpi_sha256"], self.summary["page"]["render_400dpi_sha256"])
        self.assertEqual(evidence["table_crop"]["bbox_px_300dpi"], self.summary["visual_evidence"]["table_crop"]["bbox_px_300dpi"])
        self.assertEqual(evidence["table_crop"]["sha256"], self.summary["visual_evidence"]["table_crop"]["sha256"])
        self.assertEqual(evidence["figure_crop"]["bbox_px_300dpi"], self.summary["visual_evidence"]["figure_crop"]["bbox_px_300dpi"])
        self.assertEqual(evidence["figure_crop"]["sha256"], self.summary["visual_evidence"]["figure_crop"]["sha256"])

    def test_candidate_table_is_review_only_14x4(self) -> None:
        table_contract = self.contract["table_candidate_contract"]
        self.assertEqual(table_contract["status"], "REVIEW_CANDIDATE_NOT_APPROVED_TRUTH")
        self.assertEqual(table_contract["required_candidate_shape"], {"rows": 14, "columns": 4})
        self.assertEqual(
            set(table_contract["canonical_candidate_source"]),
            {"pdfplumber_native_line", "camelot_lattice"},
        )
        self.assertTrue(table_contract["must_not_infer_missing_cells"])
        self.assertTrue(table_contract["must_not_majority_vote_critical_cells"])
        self.assertTrue(table_contract["human_qa_required_before_indexing"])
        required_cell_fields = set(table_contract["required_cell_fields"])
        self.assertTrue({"bbox_px_300dpi", "disagreement_ids", "review_status"}.issubset(required_cell_fields))

    def test_engine_disagreement_matrix_matches_benchmark(self) -> None:
        contract_outputs = self.contract["engine_outputs"]
        summary_outputs = self.summary["table_extractors"]
        for engine_name, summary_value in summary_outputs.items():
            self.assertIn(engine_name, contract_outputs)
            self.assertEqual(contract_outputs[engine_name]["shape"], summary_value["shape"])
        self.assertEqual(contract_outputs["pdfplumber_native_line"]["role"], "canonical_candidate_engine")
        self.assertEqual(contract_outputs["camelot_lattice"]["role"], "canonical_candidate_engine")
        disagreement_shapes = {
            tuple(value["shape"])
            for value in contract_outputs.values()
            if value["role"] == "disagreement_evidence"
        }
        self.assertTrue({(17, 6), (17, 2), (13, 4), (0, 0), (9, 4), (8, 4)}.issubset(disagreement_shapes))

    def test_dashboard_review_blocks_approval_until_resolved(self) -> None:
        dashboard = self.contract["dashboard_handoff"]
        self.assertEqual(dashboard["view"], "side_by_side_review")
        self.assertEqual(dashboard["right_panel"]["rendering"], "react_components_no_raw_html")
        self.assertEqual(dashboard["right_panel"]["approve_button_default"], "disabled")
        blockers = set(dashboard["approval_blockers"])
        self.assertTrue(
            {
                "missing_source_crop_hash",
                "unresolved_critical_disagreement",
                "missing_document_version_mapping",
                "approved_for_ai_use_not_true",
                "reviewer_identity_missing",
            }.issubset(blockers)
        )

    def test_no_production_write_or_live_control_in_contract(self) -> None:
        assertions = self.contract["production_write_assertions"]
        self.assertTrue(assertions["no_supabase_write_in_source_contract"])
        self.assertTrue(assertions["no_n8n_update_execute_publish_archive"])
        self.assertTrue(assertions["no_git_remote_action"])
        self.assertEqual(assertions["audit_log_policy"], "INSERT_ONLY")
        lowered = CONTRACT.read_text(encoding="utf-8").lower()
        forbidden = [
            "update_workflow",
            "execute_workflow",
            "publish_workflow",
            "archive_workflow",
            "supabase db push",
            "git push",
        ]
        for token in forbidden:
            self.assertNotIn(token, lowered)

    def test_checkpoint_records_done_source_only_and_blk004_open(self) -> None:
        self.assertIn("Status: `DONE_SOURCE_ONLY`", self.checkpoint)
        self.assertIn("BLK-004 remains `OPEN`", self.checkpoint)
        self.assertIn("No Supabase write/import/chunk/embedding", self.checkpoint)
        self.assertIn("No n8n update/execute/publish/archive", self.checkpoint)
        self.assertIn("No Git remote action", self.checkpoint)


if __name__ == "__main__":
    unittest.main()
