#!/usr/bin/env python3
"""Regression tests for the R05-A32 BLK-003 source-only binding package."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from r05_a32_blk003_reference_binding_package import (
    DEFAULT_A31_REPORT_JSON,
    DEFAULT_CATALOG_CSV,
    DEFAULT_RETIREMENT_CSV,
    PLAN_FIELDS,
    build_package,
    write_outputs,
)


class R05A32Blk003ReferenceBindingPackageTest(unittest.TestCase):
    def test_real_inputs_build_source_only_ready_package(self) -> None:
        package = build_package()

        self.assertEqual(
            package["decision"],
            "BLK003_READY_FOR_LIVE_PREFLIGHT_AND_APPROVAL_SOURCE_ONLY",
        )
        self.assertFalse(package["errors"])
        self.assertEqual(package["summary"]["reference_binding_count"], 12)
        self.assertEqual(package["summary"]["internal_sop_retirement_count"], 10)
        self.assertEqual(
            package["summary"]["blk003_status_after_a32"],
            "OPEN_READY_FOR_LIVE_PREFLIGHT_AND_APPROVAL",
        )
        self.assertEqual(
            package["summary"]["next_allowed_after_blk003_live_verify"],
            "BLK-005_EMBEDDING_RECERTIFICATION",
        )
        self.assertFalse(package["summary"]["production_ai_use_allowed"])
        self.assertEqual(package["remote_operations"], {"drive": [], "git": [], "n8n": [], "supabase": []})

    def test_binding_rows_preserve_ref_identity_and_deny_retrieval(self) -> None:
        package = build_package()
        rows = package["binding_rows"]

        self.assertEqual(len(rows), 12)
        self.assertEqual(len({row["document_code"] for row in rows}), 12)
        self.assertEqual(len({row["drive_file_id"] for row in rows}), 12)
        self.assertEqual(len({row["binary_sha256"] for row in rows}), 12)
        for row in rows:
            self.assertTrue(row["document_code"].startswith("REF-"))
            self.assertTrue(row["version_label"].startswith("ref-a32-20260630-"))
            self.assertEqual(row["raw_file_action"], "CREATE_OR_VERIFY_RAW_FILE_HASH_STATUS_VERIFIED")
            self.assertEqual(row["version_action"], "CREATE_IMMUTABLE_INGEST_VERSION_FROM_VERIFIED_RAW_FILE")
            self.assertEqual(row["current_pointer_action"], "SET_DOCUMENT_CURRENT_VERSION_TO_NEW_REF_INGEST_VERSION")
            self.assertEqual(row["approved_for_ai_use"], "FALSE")
            self.assertEqual(row["document_version_hash_status"], "verified")
            self.assertEqual(row["document_version_index_status"], "excluded")
            self.assertEqual(row["production_retrieval"], "DENY_UNTIL_BLK005_BLK006_BLK007_PASS")
            self.assertEqual(row["live_required"], "TRUE")

    def test_retirement_rows_are_reversible_and_not_hard_delete(self) -> None:
        package = build_package()
        rows = package["retirement_rows"]

        self.assertEqual([row["document_code"] for row in rows], [f"GMP-SOP-{index:03d}" for index in range(1, 11)])
        for row in rows:
            self.assertEqual(row["target_document_status"], "archived")
            self.assertEqual(row["target_approved_for_ai_use"], "FALSE")
            self.assertEqual(row["current_version_action"], "PRESERVE_IMMUTABLE_EVIDENCE")
            self.assertEqual(row["hard_delete"], "FALSE")
            self.assertIn("RESTORE_PRE_A32_STATUS_FROM_LIVE_SNAPSHOT", row["rollback_action"])

    def test_sql_artifacts_are_guarded_and_preflight_is_read_only(self) -> None:
        package = build_package()
        sql = package["_generated_sql"]

        preflight = sql["preflight"].lower()
        for forbidden in ("insert ", "update ", "delete ", "alter table", "create table", "drop "):
            self.assertNotIn(forbidden, preflight)
        self.assertIn("existing_ref_documents", preflight)
        self.assertIn("current_version_integrity", preflight)

        apply_proposal = sql["apply_proposal"]
        self.assertIn("NOT FOR APPLY", apply_proposal)
        self.assertIn("crave.a32_apply_approved", apply_proposal)
        self.assertIn("raise exception", apply_proposal.lower())
        self.assertIn("record_origin='ingest'", apply_proposal)
        self.assertIn("raw_files.status='verified'", apply_proposal)

        rollback = sql["rollback_proposal"]
        self.assertIn("ROLLBACK PROPOSAL", rollback)
        self.assertIn("No hard delete", rollback)

    def test_missing_a31_prerequisite_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_a31 = Path(temp_dir) / "a31.json"
            payload = json.loads(DEFAULT_A31_REPORT_JSON.read_text(encoding="utf-8"))
            payload["summary"]["blk004_status_after_a31"] = "OPEN"
            bad_a31.write_text(json.dumps(payload), encoding="utf-8")

            package = build_package(a31_report_json=bad_a31)

        self.assertEqual(package["decision"], "FAIL_CLOSED_BINDING_PACKAGE_INVALID")
        self.assertTrue(any("BLK-004" in error for error in package["errors"]))

    def test_catalog_ai_approval_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tampered_catalog = Path(temp_dir) / "catalog.csv"
            with DEFAULT_CATALOG_CSV.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["approved_for_ai_use"] = "True"
            with tampered_catalog.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            package = build_package(catalog_csv=tampered_catalog)

        self.assertEqual(package["decision"], "FAIL_CLOSED_BINDING_PACKAGE_INVALID")
        self.assertTrue(any("approved_for_ai_use" in error for error in package["errors"]))

    def test_write_outputs_creates_all_expected_artifacts(self) -> None:
        package = build_package()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = write_outputs(
                package,
                plan_csv=root / "plan.csv",
                plan_json=root / "plan.json",
                preflight_sql=root / "preflight.sql",
                apply_proposal_sql=root / "apply.sql",
                rollback_proposal_sql=root / "rollback.sql",
                report_json=root / "report.json",
            )

            for name in ("plan.csv", "plan.json", "preflight.sql", "apply.sql", "rollback.sql", "report.json"):
                self.assertTrue((root / name).is_file(), name)
            with (root / "plan.csv").open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PLAN_FIELDS)
                self.assertEqual(len(list(reader)), 12)
            retained_report = json.loads((root / "report.json").read_text(encoding="utf-8"))

        self.assertEqual(report["decision"], "BLK003_READY_FOR_LIVE_PREFLIGHT_AND_APPROVAL_SOURCE_ONLY")
        self.assertEqual(retained_report["summary"]["reference_binding_count"], 12)
        self.assertIn("preflight_sql", retained_report["outputs"])


if __name__ == "__main__":
    unittest.main()
