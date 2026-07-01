#!/usr/bin/env python3
"""Regression tests for post-A36 BLK-005/006/007 live disposition."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "PROJECT_PROGRESS.md"
BLOCKERS = ROOT / "docs/progress/BLOCKERS.md"
A33_REPORT = ROOT / "work/r05_a33_blk005_embedding_recertification_report.json"
A34_REPORT = ROOT / "work/r05_a34_blk006_lineage_and_citation_readiness_report.json"
A35_REPORT = ROOT / "work/r05_a35_blk007_agent_gate_precheck_report.json"
A36_REPORT = ROOT / "work/r05_a36_route_b1_blk006_live_report.json"
P0_MANIFEST = ROOT / "docs/checkpoints/search-upgrade/P0-closure-readiness-manifest.json"


class R05A33A34A35LiveProgressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.progress = PROGRESS.read_text(encoding="utf-8")
        cls.blockers = BLOCKERS.read_text(encoding="utf-8")
        cls.a33 = json.loads(A33_REPORT.read_text(encoding="utf-8"))
        cls.a34 = json.loads(A34_REPORT.read_text(encoding="utf-8"))
        cls.a35 = json.loads(A35_REPORT.read_text(encoding="utf-8"))
        cls.a36 = json.loads(A36_REPORT.read_text(encoding="utf-8"))
        cls.p0_manifest = json.loads(P0_MANIFEST.read_text(encoding="utf-8"))

    def test_active_action_is_r08_after_consumed_consolidated_p0_final_check(self) -> None:
        self.assertIn("active_action: R08-A02", self.progress)
        r05_a36_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A36 |"))
        r05_a37_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A37 |"))
        r05_a38_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A38 |"))
        r05_a39_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A39 |"))
        r05_a40_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A40 |"))
        r05_a41_line = next(line for line in self.progress.splitlines() if line.startswith("| R05-A41 |"))
        p0_final_line = next(line for line in self.progress.splitlines() if line.startswith("| P0-FINAL-CHECK |"))
        self.assertIn("| `DONE` |", r05_a36_line)
        self.assertIn("BLK-006 CLOSED", r05_a36_line)
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a37_line)
        self.assertIn("Route B2", r05_a37_line)
        self.assertIn("| `DONE` |", r05_a38_line)
        self.assertIn("030b agent evidence foundation", r05_a38_line)
        self.assertIn("| `DONE` |", r05_a39_line)
        self.assertIn("eval-v2/health assertions", r05_a39_line)
        self.assertIn("| `DONE_SOURCE_ONLY` |", r05_a40_line)
        self.assertIn("controlled TKTL agent canary source", r05_a40_line)
        self.assertIn("| `DONE` |", r05_a41_line)
        self.assertIn("live U10/U11/U13/U14/U15", r05_a41_line)
        self.assertIn("| `DONE_SOURCE_ONLY` |", p0_final_line)
        self.assertIn("FINAL_CHECK_PASS", p0_final_line)
        self.assertIn("PASS_WITH_CAVEAT", p0_final_line)
        self.assertIn("review_gate: NONE", self.progress)
        self.assertIn("review_scope: NONE", self.progress)

    def test_current_p0_blocker_disposition(self) -> None:
        expected = {
            "BLK-001": "CLOSED",
            "BLK-002": "CLOSED",
            "BLK-003": "CLOSED",
            "BLK-004": "CLOSED",
            "BLK-005": "CLOSED",
            "BLK-006": "CLOSED",
            "BLK-007": "CLOSED",
        }
        for blocker_id, status in expected.items():
            progress_line = next(line for line in self.progress.splitlines() if line.startswith(f"| {blocker_id} |"))
            blockers_line = next(line for line in self.blockers.splitlines() if line.startswith(f"| {blocker_id} |"))
            self.assertIn(f"| `{status}` |", progress_line)
            self.assertTrue(blockers_line.rstrip().endswith(f"| {status} |"), blockers_line)

    def test_a33_closes_blk005_by_fail_closed_exclusion(self) -> None:
        self.assertEqual(
            self.a33["decision"],
            "BLK005_LIVE_RECERTIFIED_CLOSED_BY_APPROVED_EXCLUSION_FAIL_CLOSED",
        )
        self.assertEqual(self.a33["liveSummary"]["postA32Binding"]["refApprovedExclusions"], 12)
        self.assertEqual(self.a33["liveSummary"]["chunkEmbeddingState"]["chunksWithEmbedding"], 65)
        self.assertEqual(self.a33["liveSummary"]["chunkEmbeddingState"]["chunksMissingEmbedding"], 0)
        self.assertEqual(self.a33["liveSummary"]["chunkEmbeddingState"]["maxEmbeddingDimensions"], 1536)
        self.assertEqual(self.a33["liveSummary"]["hybridGateState"]["gateEligibleChunks"], 0)
        self.assertEqual(self.a33["blockerDisposition"]["BLK-005"], "CLOSED")

    def test_a34_records_historical_partial_lineage_state(self) -> None:
        self.assertEqual(
            self.a34["decision"],
            "BLK006_LINEAGE_CLOSED_RUNTIME_POSITIVE_BLOCKED_BY_ZERO_ELIGIBLE_RETRIEVAL",
        )
        self.assertEqual(self.a34["migration030Verification"]["decision"], "MIGRATION030_LINEAGE_LIVE_VERIFIED")
        self.assertEqual(self.a34["migration030Verification"]["chunkLinkState"]["totalChunks"], 65)
        self.assertEqual(self.a34["migration030Verification"]["chunkLinkState"]["chunksWithDocumentVersionId"], 65)
        self.assertEqual(self.a34["migration030Verification"]["chunkLinkState"]["invalidLinks"], 0)
        self.assertFalse(self.a34["migration030Verification"]["runtimeRetrievalState"]["positiveCitationPossibleNow"])
        self.assertEqual(
            self.a34["blockerDisposition"]["BLK-006"],
            "OPEN_PARTIAL_LINEAGE_LIVE_VERIFIED_RUNTIME_POSITIVE_BLOCKED",
        )

    def test_a36_closes_blk006_with_positive_citation_and_zero_residue(self) -> None:
        self.assertEqual(
            self.a36["decision"],
            "BLK006_CLOSED_DATABASE_RUNTIME_POSITIVE_CITATION_ROLLBACK_SAFE",
        )
        retry = self.a36["successfulRetry"]
        self.assertEqual(retry["decision"], "PASS_POSITIVE_CITATION_ASSERTED_AND_ZERO_RESIDUE")
        self.assertFalse(retry["commitPresent"])
        self.assertEqual(retry["positiveAssertionsBeforeRollback"]["hybridRetrievalExactFixtureCount"], 1)
        self.assertEqual(retry["positiveAssertionsBeforeRollback"]["groundedAiQuerySourcesCount"], 1)
        self.assertEqual(retry["positiveAssertionsBeforeRollback"]["validChunkToImmutableVersionLineageCount"], 1)
        self.assertTrue(all(value == 0 for value in retry["rollbackResidue"].values()))
        self.assertEqual(self.a36["independentResidueProbe"]["decision"], "PASS_ZERO_RESIDUE")
        self.assertTrue(all(value == 0 for value in self.a36["independentResidueProbe"]["residue"].values()))
        self.assertEqual(
            self.a36["blockerDisposition"]["BLK-006"],
            "CLOSED_DATABASE_RUNTIME_POSITIVE_CITATION_LIVE_VERIFIED",
        )

    def test_a35_blocks_agent_until_runtime_citation_exists(self) -> None:
        self.assertEqual(
            self.a35["decision"],
            "BLK007_AGENT_CANARY_NOT_ALLOWED_UNTIL_BLK006_RUNTIME_POSITIVE",
        )
        self.assertEqual(self.a35["precheck"]["u11CitationGrounding"], "BLOCKED_BY_NO_RUNTIME_POSITIVE_CITATION")
        self.assertEqual(self.a35["remoteOperations"], {"supabase": [], "n8n": [], "drive": [], "git": []})

    def test_p0_manifest_is_ready_for_final_check_with_no_open_p0(self) -> None:
        self.assertEqual(self.p0_manifest["decision"], "READY_FOR_FINAL_CHECK")
        self.assertEqual(self.p0_manifest["openP0Blockers"], [])
        checks = {row["id"]: row["status"] for row in self.p0_manifest["checks"]}
        self.assertEqual(checks["P0-C01"], "PASS")
        self.assertEqual(checks["P0-C05"], "PASS")
        self.assertEqual(checks["P0-C06"], "PASS")
        self.assertEqual(checks["P0-C07"], "PASS")
        self.assertEqual(checks["P0-C08"], "PASS")


if __name__ == "__main__":
    unittest.main()
