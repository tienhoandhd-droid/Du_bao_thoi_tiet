#!/usr/bin/env python3
"""Source-only tests for the secret-safe two-user canary operator."""

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import wf06_two_user_canary_operator as operator


class WF06TwoUserCanaryOperatorTests(unittest.TestCase):
    def test_dry_run_has_no_external_calls(self):
        output = io.StringIO()
        with mock.patch.object(operator, "run_cli") as cli, mock.patch.object(
            operator, "request_json"
        ) as request, redirect_stdout(output):
            self.assertEqual(operator.dry_run(), 0)
        cli.assert_not_called()
        request.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["network_requests"], 0)
        self.assertEqual(payload["subprocess_calls"], 0)
        self.assertEqual(payload["planned_auth_users"], 2)
        self.assertEqual(payload["app_role_assignments"], 0)

    def test_load_keys_selects_named_legacy_keys_without_printing(self):
        response = mock.Mock(
            stdout=json.dumps(
                [
                    {"name": "anon", "api_key": "anon-secret"},
                    {"name": "service_role", "api_key": "service-secret"},
                ]
            )
        )
        with mock.patch.object(operator, "run_cli", return_value=response):
            self.assertEqual(operator.load_project_keys(), ("service-secret", "anon-secret"))

    def test_execute_always_cleans_up_on_canary_failure(self):
        fake_canary = {
            "endpoint": "redacted",
            "evidence": [],
            "failures": ["expected failure"],
        }

        def canary_run(_config):
            print(json.dumps(fake_canary))
            return 1

        with mock.patch.object(operator, "load_project_keys", return_value=("svc", "anon")), mock.patch.object(
            operator, "create_user", side_effect=["id-a", "id-b"]
        ), mock.patch.object(operator, "run_setup_sql"), mock.patch.object(
            operator, "sign_in", side_effect=["jwt-a", "jwt-b"]
        ), mock.patch.object(operator.canary, "run_execute", side_effect=canary_run), mock.patch.object(
            operator, "delete_user"
        ) as delete_user, mock.patch.object(operator, "verify_cleanup"), redirect_stdout(io.StringIO()):
            self.assertEqual(operator.execute(), 1)
        self.assertEqual(delete_user.call_count, 2)
        delete_user.assert_any_call("svc", "id-a")
        delete_user.assert_any_call("svc", "id-b")

    def test_setup_sql_is_minimal_and_user_specific(self):
        source = operator.SETUP_SQL.read_text(encoding="utf-8")
        self.assertIn("'GMP-SOP-001'", source)
        self.assertIn("'GMP-SOP-002'", source)
        self.assertIn("can_view, can_edit, can_approve", source)
        self.assertIn("true,\n  false,\n  false", source)
        self.assertNotIn("insert into public.user_roles", source.lower())
        self.assertNotIn("update public.documents", source.lower())
        self.assertNotIn("delete from public.documents", source.lower())

    def test_execute_requires_explicit_guard_flag(self):
        with self.assertRaises(SystemExit):
            operator.main(["--execute"])

    def test_partial_user_creation_still_cleans_first_user(self):
        with mock.patch.object(operator, "load_project_keys", return_value=("svc", "anon")), mock.patch.object(
            operator, "create_user", side_effect=["id-a", RuntimeError("create B failed")]
        ), mock.patch.object(operator, "delete_user") as delete_user, mock.patch.object(
            operator, "verify_cleanup"
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(operator.execute(), 1)
        delete_user.assert_called_once_with("svc", "id-a")

    def test_source_does_not_print_secret_variables(self):
        source = Path(operator.__file__).read_text(encoding="utf-8")
        self.assertNotIn("print(service_key", source)
        self.assertNotIn("print(anon_key", source)
        self.assertNotIn("print(password_a", source)
        self.assertNotIn("print(password_b", source)
        self.assertNotIn("print(jwt_a", source)
        self.assertNotIn("print(jwt_b", source)


if __name__ == "__main__":
    unittest.main()
