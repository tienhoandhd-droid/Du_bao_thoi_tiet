#!/usr/bin/env python3
"""Static regression checks for the R05-A42 controlled live canary source."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/r05_a41_controlled_agent_canary_live_workflow.js"


class R05A41ControlledAgentCanaryLiveSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.lower = cls.source.lower()

    def test_javascript_syntax_and_identity(self) -> None:
        subprocess.run(
            ["node", "--check", str(SOURCE)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("TKTL R05-A42 Controlled Agent Canary", self.source)
        self.assertIn("R05-A42-live-v1", self.source)

    def test_credentials_are_allowlisted_and_secret_free(self) -> None:
        self.assertIn("newCredential('GMP-check')", self.source)
        self.assertIn("newCredential('OpenAl')", self.source)
        self.assertEqual(self.source.count("newCredential('x-api-key')"), 2)
        self.assertEqual(self.source.count("genericAuthType: 'httpHeaderAuth'"), 2)
        self.assertNotIn("__REDACTED_SUPABASE_ANON_KEY__", self.source)
        self.assertNotIn("service_role", self.lower)
        self.assertNotIn("variables.", self.lower)
        self.assertNotIn("community", self.lower)
        self.assertNotIn("crypto", self.lower)

    def test_eval_v2_has_five_non_null_golden_question_bindings(self) -> None:
        self.assertIn("model_tag, n_questions, score_mean, score_min, passed", self.source)
        self.assertNotIn("avg_reciprocal_rank", self.source)
        self.assertIn("gate_question AS", self.source)
        self.assertIn("gate.question_id", self.source)
        self.assertNotIn("eval_run.id, NULL::uuid", self.source)
        for gate in ("U10", "U11", "U13", "U14", "U15"):
            self.assertIn(f"R05-A42-{gate}", self.source)
        self.assertIn("CROSS JOIN gate_question gate", self.source)

    def test_retrieval_and_evidence_boundaries_remain_controlled(self) -> None:
        self.assertIn("/auth/v1/user", self.source)
        self.assertIn("/rest/v1/rpc/hybrid_search_v3", self.source)
        self.assertIn("p_user_id", self.source)
        self.assertIn("public.retrieval_candidates", self.source)
        self.assertIn("public.ai_query_sources", self.source)
        self.assertIn("public.system_health_metrics", self.source)
        self.assertIn("public.eval_results", self.source)
        self.assertIn("eval_gate_pending_independent_verify", self.source)
        self.assertIn("health_gate_pending_independent_verify", self.source)
        self.assertNotIn("crave_evaluate_eval_v2_release_gate_v1((SELECT id FROM eval_run))", self.source)

    def test_live_eval_runs_legacy_columns_are_respected(self) -> None:
        self.assertIn("model_tag, n_questions, score_mean, score_min, passed", self.source)
        self.assertIn("'R05-A42-CONTROLLED-CANARY', dataset.question_count", self.source)
        self.assertNotIn("avg_reciprocal_rank", self.source)

    def test_live_eval_results_legacy_columns_are_respected(self) -> None:
        self.assertIn(
            "run_id, question_id, answer, score_faithfulness, score_relevancy, score_context_recall, grounded_pct, passed, raw_json",
            self.source,
        )
        self.assertNotIn("question_id, expected_doc", self.source)


if __name__ == "__main__":
    unittest.main()
