#!/usr/bin/env python3
"""Regression for S1 migration governance closure of BLK-008 and BLK-009."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs/governance/s1-migration-governance-adr.md"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/S1-GOV-001-migration-governance-adr.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/S1-GOV-001-migration-governance-adr-manifest.json"
LEDGER = ROOT / "docs/database/live-migration-ledger.md"
MIGRATION_LANE = ROOT / "supabase/MIGRATION_LANE.md"
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"


class S1MigrationGovernanceAdrTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adr = ADR.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.migration_lane = MIGRATION_LANE.read_text(encoding="utf-8")
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")

    def test_adr_closes_blk008_with_manual_recovery_not_auto_downcast(self) -> None:
        required = [
            "BLK-008",
            "021d_eval_score_columns_fix",
            "manual-recovery",
            "numeric(5,4)",
            "numeric(5,2)",
            "MUST NOT auto-downcast",
            "Freeze eval writers",
            "Snapshot or export",
            "PITR",
            "MUST NOT delete `eval_runs` or `eval_results`",
            "MUST NOT update, truncate or delete `audit_log`",
        ]
        for phrase in required:
            self.assertIn(phrase, self.adr)

    def test_adr_closes_blk009_without_migration_repair(self) -> None:
        required = [
            "BLK-009",
            "016_eval_harness.sql",
            "021c_eval_function_v3_or_tsquery",
            "supabase migration repair",
            "MUST NOT run `supabase migration repair`",
            "docs/database/live-migration-ledger.md",
            "supabase db push --linked --dry-run",
        ]
        for phrase in required:
            self.assertIn(phrase, self.adr)

    def test_manifest_records_source_only_closure_and_remaining_blk010(self) -> None:
        self.assertEqual(self.manifest["projectId"], "bdttccztjtrcaztjgkot")
        self.assertEqual(self.manifest["action"], "S1-GOV-001")
        self.assertEqual(self.manifest["status"], "DONE_SOURCE_ONLY")
        self.assertEqual(set(self.manifest["scope"]), {"BLK-008", "BLK-009"})
        self.assertEqual(set(self.manifest["blockersClosed"]), {"BLK-008", "BLK-009"})
        self.assertEqual(set(self.manifest["blockersRemainingOpen"]), {"BLK-010"})
        self.assertEqual(self.manifest["remoteOperations"], {"supabase": [], "n8n": [], "git": [], "github": []})
        self.assertIn("MUST_NOT_AUTO_DOWNCAST_021D_TO_NUMERIC_5_4", self.manifest["prohibitions"])
        self.assertIn("MUST_NOT_REPAIR_MIGRATION_HISTORY_WITHOUT_SEPARATE_ADR_APPROVAL", self.manifest["prohibitions"])

    def test_progress_and_blocker_trackers_close_only_blk008_and_blk009(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)
        self.assertIn("| S1-GOV-001 |", self.progress)
        s1_line = next(line for line in self.progress.splitlines() if line.startswith("| S1-GOV-001 |"))
        self.assertIn("| `DONE_SOURCE_ONLY` |", s1_line)
        self.assertIn("BLK-008/009 CLOSED", s1_line)
        expected = {"BLK-008": "CLOSED", "BLK-009": "CLOSED", "BLK-010": "CLOSED"}
        for blocker_id, status in expected.items():
            progress_line = next(line for line in self.progress.splitlines() if line.startswith(f"| {blocker_id} |"))
            tracker_line = next(line for line in self.blockers.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertIn(f"| `{status}` |", progress_line)
            self.assertTrue(tracker_line.rstrip().endswith(f"| {status} |"), tracker_line)

    def test_ledger_and_migration_lane_reference_governance_adr(self) -> None:
        self.assertIn("s1-migration-governance-adr.md", self.ledger)
        self.assertIn("BLK-008", self.ledger)
        self.assertIn("BLK-009", self.ledger)
        self.assertIn("s1-migration-governance-adr.md", self.migration_lane)
        self.assertIn("021d", self.migration_lane)
        self.assertIn("016/021c", self.migration_lane)

    def test_checkpoint_records_no_remote_operations_and_no_production_go(self) -> None:
        for phrase in [
            "No Supabase live mutation",
            "No n8n mutation",
            "No Git remote action",
            "No production GO",
            "BLK-010 remains OPEN",
        ]:
            self.assertIn(phrase, self.checkpoint)

    def test_manifest_hashes_match_artifacts_after_finalization(self) -> None:
        mutable_artifacts = {
            "PROJECT_PROGRESS.md",
            "docs/progress/BLOCKERS.md",
            "scripts/test_s1_migration_governance_adr.py",
        }
        for artifact in self.manifest["artifacts"]:
            self.assertNotEqual(artifact["sha256"], "TBD", artifact["path"])
            if artifact["path"] in mutable_artifacts:
                self.assertTrue((ROOT / artifact["path"]).exists(), artifact["path"])
                continue
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
