#!/usr/bin/env python3
"""Source-only tests for the WF-06 positive RLS canary runner."""

import json
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/wf06_positive_rls_canary.py"
PLAN = ROOT / "docs/checkpoints/search-upgrade/R01-A07-positive-rls-canary-plan.md"
sys.path.insert(0, str(ROOT / "scripts"))

import wf06_positive_rls_canary as canary


class WF06PositiveRlsCanaryTests(unittest.TestCase):
    def test_dry_run_lists_owner_and_cross_user_marker_cases(self):
        env = os.environ.copy()
        env["CRAVE_WF06_CANARY_A_ONLY_KEYWORD"] = "SYNTHETIC-DOC-A"
        env["CRAVE_WF06_CANARY_B_ONLY_KEYWORD"] = "SYNTHETIC-DOC-B"
        completed = subprocess.run(
            ["python3", str(RUNNER), "--dry-run"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["network_requests"], 0)
        self.assertEqual(len(payload["planned_cases"]), 6)
        planned = "\n".join(payload["planned_cases"])
        self.assertIn("user_a_can_read_a_marker", planned)
        self.assertIn("user_b_can_read_b_marker", planned)
        self.assertIn("total_count>0", planned)
        self.assertIn("user_a_cannot_read_b_marker", planned)
        self.assertIn("user_b_cannot_read_a_marker", planned)
        self.assertIn("total_count=0", planned)

    def test_runner_execute_cases_include_nonzero_expectations(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"user_a_can_read_a_marker"', source)
        self.assertIn('"user_b_can_read_b_marker"', source)
        self.assertIn('"nonzero"', source)
        self.assertIn('"User-Agent": CLIENT_USER_AGENT', source)
        self.assertIn('"Accept": "application/json"', source)
        self.assertIn("expected total_count>0", source)
        self.assertIn("expected total_count=0", source)

    def test_checkpoint_requires_owner_marker_positive_assertions(self):
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("User A searching the A-only marker", plan)
        self.assertIn("User B searching the B-only marker", plan)
        self.assertIn("total_count>0", plan)
        self.assertIn("cannot substitute for marker proof", plan)

    def test_boolean_total_count_is_rejected(self):
        body = {
            "success": True,
            "documents": [],
            "total_count": True,
            "limit": 20,
            "offset": 0,
        }
        failures = canary.assert_success_response(
            "boolean_count",
            200,
            {"access-control-allow-origin": canary.ALLOWED_ORIGIN},
            body,
        )
        self.assertIn("boolean_count: total_count is not an integer", failures)
        self.assertIsNone(canary.total_count(body))

    def test_execute_fails_closed_when_count_is_boolean(self):
        config = canary.CanaryConfig(True, True, "A-ONLY", "B-ONLY", "SOP")
        boolean_body = {
            "success": True,
            "documents": [],
            "total_count": True,
            "limit": 20,
            "offset": 0,
        }
        with mock.patch.dict(
            os.environ,
            {"CRAVE_WF06_JWT_A": "jwt-a", "CRAVE_WF06_JWT_B": "jwt-b"},
            clear=False,
        ), mock.patch.object(
            canary,
            "post_webhook",
            return_value=(
                200,
                {"access-control-allow-origin": canary.ALLOWED_ORIGIN},
                boolean_body,
            ),
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(canary.run_execute(config), 1)

    def test_sanitized_error_text_limits_non_json_body(self):
        text = "x" * 300
        self.assertEqual(canary.sanitized_error_text({"_non_json_body": text}), "x" * 160)
        self.assertEqual(canary.sanitized_error_text({"error": "Không có quyền"}), "Không có quyền")
        self.assertIsNone(canary.sanitized_error_text(["not", "dict"]))


if __name__ == "__main__":
    unittest.main()
