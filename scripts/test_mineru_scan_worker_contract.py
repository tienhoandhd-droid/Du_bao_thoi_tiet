#!/usr/bin/env python3
"""Kiểm tra tĩnh contract MinerU source-only của CRAVE."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "n8n/workflow-contracts/TKTL-R08-mineru-scan-worker.contract.json"
)
ARCHITECTURE_PATH = ROOT / "docs/architecture/crave-mineru-scan-pipeline.md"


class MinerUScanWorkerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")

    def test_source_only_and_no_live_mutation(self) -> None:
        self.assertEqual(self.contract["live_status"], "SOURCE_ONLY_NOT_DEPLOYED")
        self.assertEqual(self.contract["production_write_default"], "DENY")
        self.assertFalse(self.contract["on_missing_or_failed_assertion"]["production_write"])
        self.assertFalse(self.contract["next_gate"]["live_mutation_authorized"])

    def test_release_is_pinned_and_external_upload_is_denied(self) -> None:
        candidate = self.contract["mineru_candidate"]
        self.assertEqual(candidate["repository"], "opendatalab/MinerU")
        self.assertEqual(candidate["release_tag"], "mineru-3.4.0-released")
        self.assertTrue(candidate["forbid_latest_tag"])
        self.assertFalse(candidate["llm_aided_config_enabled"])
        self.assertFalse(candidate["external_document_upload_allowed"])
        self.assertTrue(candidate["private_local_worker_required"])

    def test_license_gate_is_not_plain_apache_assumption(self) -> None:
        gate = self.contract["license_gate"]
        self.assertTrue(gate["apache_2_based_with_additional_terms"])
        self.assertTrue(gate["online_service_attribution_review_required"])
        self.assertTrue(gate["legal_owner_decision_required_before_production"])
        self.assertRegex(self.architecture.lower(), r"điều\s+kiện bổ sung")

    def test_crave_owns_durable_jobs_and_idempotency(self) -> None:
        boundary = self.contract["job_boundary"]
        self.assertEqual(boundary["canonical_state_owner"], "CRAVE_INGEST_JOB_LEDGER")
        self.assertFalse(boundary["mineru_task_state_is_durable"])
        self.assertTrue(boundary["reconcile_output_hash_before_retry"])
        self.assertFalse(boundary["duplicate_production_write_allowed"])
        self.assertEqual(
            set(boundary["idempotency_key_fields"]),
            {
                "document_version_id",
                "raw_sha256",
                "page_window_start",
                "page_window_end",
                "parser_lock_hash",
            },
        )

    def test_adapter_rejects_schema_guessing(self) -> None:
        adapter = self.contract["output_adapter"]
        self.assertTrue(adapter["reject_unknown_mineru_version"])
        self.assertTrue(adapter["reject_unknown_backend"])
        self.assertFalse(adapter["markdown_is_canonical"])
        self.assertEqual(adapter["primary_structured_artifact"], "middle.json")
        self.assertFalse(adapter["content_list_v2_production_contract_allowed"])
        required = set(adapter["required_provenance"])
        self.assertTrue(
            {
                "document_version_id",
                "raw_sha256",
                "page_number",
                "original_bbox",
                "normalized_bbox_0_1000",
                "source_crop_sha256",
                "parser_lock_hash",
            }.issubset(required)
        )

    def test_mineru_is_one_engine_not_truth(self) -> None:
        gate = self.contract["multi_engine_gate"]
        self.assertGreaterEqual(gate["required_independent_paths_for_scanned_gmp"], 3)
        self.assertTrue(gate["mineru_counts_as_one_path"])
        self.assertFalse(gate["mineru_can_self_approve"])
        self.assertFalse(gate["majority_vote_can_approve_critical_content"])
        self.assertTrue(
            {"number", "unit", "table_cell", "diagram_label", "reading_order"}.issubset(
                set(gate["critical_fields"])
            )
        )

    def test_human_qa_and_current_version_remain_mandatory(self) -> None:
        assertions = set(self.contract["promotion_assertions"])
        self.assertIn("human_qa_approved_for_gmp_critical_content", assertions)
        self.assertIn("current_document_version", assertions)
        self.assertIn("license_allowed_or_curated", assertions)
        self.assertIn("approved_for_ai_use", assertions)
        self.assertEqual(
            self.contract["on_missing_or_failed_assertion"]["state"], "QUARANTINED"
        )

    def test_n8n_boundary_preserves_crave_constraints(self) -> None:
        boundary = self.contract["n8n_boundary"]
        self.assertFalse(boundary["binary_or_base64_in_long_item_chain_allowed"])
        self.assertFalse(boundary["public_unauthenticated_worker_allowed"])
        self.assertFalse(boundary["new_n8n_credential_allowed_without_change_control"])
        self.assertFalse(boundary["n8n_variables_allowed"])
        self.assertFalse(boundary["community_nodes_allowed"])
        self.assertFalse(boundary["crypto_in_code_node_allowed"])
        self.assertFalse(boundary["live_update_execute_publish_archive_allowed"])

    def test_oq_is_fail_closed_and_resource_measured(self) -> None:
        oq = self.contract["oq_gate"]
        self.assertEqual(oq["fixture_count"], 5)
        self.assertEqual(len(oq["fixture_types"]), 5)
        self.assertEqual(oq["accepted_block_provenance_coverage"], 1.0)
        self.assertFalse(oq["critical_auto_promotion_allowed"])
        self.assertFalse(oq["corrupt_or_password_input_may_create_chunks"])
        self.assertFalse(oq["restart_may_create_duplicate"])
        self.assertTrue(oq["resource_report_required"])
        self.assertFalse(oq["network_egress_during_parse_allowed"])


if __name__ == "__main__":
    unittest.main()
