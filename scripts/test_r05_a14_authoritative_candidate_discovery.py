#!/usr/bin/env python3
"""Static assertions for R05-A14 authoritative candidate metadata discovery."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "work/r05_a14_authoritative_candidate_discovery_report.json"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A14-authoritative-candidate-discovery-manifest.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A14-authoritative-candidate-discovery.md"
MAPPING = ROOT / "work/r05_authoritative_12_file_mapping.csv"

REQUIRED_CODES = [
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
]


class R05A14AuthoritativeCandidateDiscoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        with MAPPING.open(encoding="utf-8", newline="") as handle:
            cls.mapping_rows = list(csv.DictReader(handle))

    def test_live_report_is_metadata_only_and_no_candidates(self) -> None:
        self.assertEqual(self.report["decision"], "METADATA_DISCOVERY_COMPLETE_NO_CANDIDATES")
        self.assertEqual(self.report["execution"]["status"], "success")
        self.assertEqual(self.report["workflow"]["id"], "60dBeaI5H1VqaqGq")
        self.assertFalse(self.report["workflow"]["active"])
        self.assertIsNone(self.report["workflow"]["active_version_id"])
        self.assertFalse(self.report["workflow"]["is_archived"])
        self.assertEqual(self.report["metadata_result"]["authoritative_confirmed_count"], 0)
        self.assertEqual(self.report["metadata_result"]["total_unique_metadata_candidates"], 0)
        self.assertEqual(self.report["metadata_result"]["all_candidates"], [])

    def test_all_required_codes_have_no_metadata_candidate_status(self) -> None:
        by_code = self.report["metadata_result"]["by_document_code"]
        self.assertEqual(list(by_code), REQUIRED_CODES)
        for code in REQUIRED_CODES:
            self.assertEqual(by_code[code]["status"], "NO_METADATA_CANDIDATE_FOUND")
            self.assertEqual(by_code[code]["candidate_count"], 0)
            self.assertEqual(by_code[code]["candidates"], [])

    def test_mapping_template_remains_unpromoted(self) -> None:
        self.assertEqual([row["document_code"] for row in self.mapping_rows], REQUIRED_CODES)
        self.assertTrue(all(row["drive_file_id"] == "REQUIRED" for row in self.mapping_rows))
        self.assertTrue(all(row["status"] == "AWAITING_AUTHORITATIVE_MAPPING" for row in self.mapping_rows))
        self.assertNotIn("AUTHORITATIVE_CONFIRMED", {row["status"] for row in self.mapping_rows})

    def test_manifest_records_scope_and_no_forbidden_remote_operations(self) -> None:
        self.assertEqual(self.manifest["rhythm"], "R05-A14")
        self.assertEqual(self.manifest["decision"], "METADATA_DISCOVERY_COMPLETE_NO_CANDIDATES")
        self.assertEqual(self.manifest["supabase"]["operations"], [])
        self.assertEqual(self.manifest["git"]["operations"], [])
        self.assertIn("execute_workflow:manual:1494021", self.manifest["n8n"]["operations"])
        self.assertEqual(self.manifest["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(self.manifest["blockers"]["BLK-004"], "OPEN")

    def test_checkpoint_denies_authoritative_closure(self) -> None:
        self.assertIn("no\nrow in `work/r05_authoritative_12_file_mapping.csv` can be promoted", self.checkpoint)
        self.assertIn("no binary download", self.checkpoint)
        self.assertIn("No Supabase write/import/indexing", self.checkpoint)
        self.assertIn("Gate: `P0`", self.checkpoint)
        self.assertIn("Decision: `HOLD`", self.checkpoint)


if __name__ == "__main__":
    unittest.main()
