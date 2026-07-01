#!/usr/bin/env python3
"""Regression for verified GitHub Issue #2 closure and BLK-010 disposition."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/S1-GOV-002-github-issue-2-closure.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/S1-GOV-002-github-issue-2-closure-manifest.json"
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"


class S1Gov002IssueClosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")

    def test_manifest_records_verified_remote_issue_state(self) -> None:
        self.assertEqual(self.manifest["projectId"], "bdttccztjtrcaztjgkot")
        self.assertEqual(self.manifest["action"], "S1-GOV-002")
        self.assertEqual(self.manifest["status"], "DONE_REMOTE_VERIFIED")
        evidence = self.manifest["githubEvidence"]
        self.assertEqual(evidence["issueNumber"], 2)
        self.assertEqual(evidence["finalState"], "CLOSED")
        self.assertEqual(evidence["stateReason"], "COMPLETED")
        self.assertEqual(evidence["closedAt"], "2026-07-01T07:30:43Z")
        self.assertEqual(evidence["pullRequestState"], "MERGED")
        self.assertEqual(evidence["successfulReleaseManifestChecks"], 2)
        self.assertEqual(evidence["failedReleaseManifestChecks"], 0)

    def test_remote_scope_is_exact_and_excludes_other_mutations(self) -> None:
        operations = self.manifest["remoteOperations"]
        self.assertEqual(
            operations["github"],
            [
                "COMMENT_ISSUE_2_WITH_APPROVED_CLOSURE_EVIDENCE",
                "CLOSE_ISSUE_2_REASON_COMPLETED",
                "READ_BACK_ISSUE_2_FINAL_STATE",
            ],
        )
        for key in ["gitPush", "pullRequestMutation", "repositorySettingsMutation", "supabase", "n8n"]:
            self.assertEqual(operations[key], [], key)

    def test_blk010_and_all_tracked_blockers_are_closed_without_production_go(self) -> None:
        self.assertEqual(self.manifest["blockersClosed"], ["BLK-010"])
        self.assertTrue(self.manifest["allTrackedBlockersClosed"])
        self.assertEqual(self.manifest["productionDecision"], "HOLD")
        self.assertFalse(self.manifest["productionGoAuthorized"])
        for tracker in [self.progress, self.blockers]:
            line = next(line for line in tracker.splitlines() if line.startswith("| BLK-010 |"))
            expected = "| `CLOSED` |" if tracker is self.progress else "| CLOSED |"
            self.assertIn(expected, line)
        self.assertIn("overall_decision: HOLD", self.progress)

    def test_progress_records_completed_action_and_consumed_remote_authorization(self) -> None:
        action_line = next(line for line in self.progress.splitlines() if line.startswith("| S1-GOV-002 |"))
        self.assertIn("| `DONE` |", action_line)
        self.assertIn("issuecomment-4851492237", action_line)
        self.assertIn("ISSUE_2_CLOSURE_CONSUMED_NO_OTHER_REMOTE_AUTHORIZATION", self.progress)

    def test_checkpoint_preserves_remote_evidence_and_release_boundary(self) -> None:
        for phrase in [
            "issuecomment-4851492237",
            "Final issue state: `CLOSED`",
            "State reason: `COMPLETED`",
            "All tracked blockers `BLK-001` through `BLK-010` are CLOSED",
            "Overall production decision remains `HOLD`",
            "No Supabase or n8n mutation occurred",
        ]:
            self.assertIn(phrase, self.checkpoint)

    def test_manifest_hashes_match_finalized_artifacts(self) -> None:
        mutable_artifacts = {
            "PROJECT_PROGRESS.md",
            "docs/progress/BLOCKERS.md",
            "scripts/test_s1_gov_002_issue_closure.py",
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
