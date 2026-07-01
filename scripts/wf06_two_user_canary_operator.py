#!/usr/bin/env python3
"""Tạo fixture hai user, chạy WF-06 canary và cleanup secret-safe.

Mặc định là dry-run: không gọi network, Supabase CLI hoặc ghi live. Chế độ execute
chỉ được dùng sau exact approval cho user/data mutation và production webhook read.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_REF = "bdttccztjtrcaztjgkot"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"
EMAIL_A = "crave-wf06-canary-a@invalid.example"
EMAIL_B = "crave-wf06-canary-b@invalid.example"
MARKER_A = "GMP-SOP-001"
MARKER_B = "GMP-SOP-002"
SETUP_SQL = ROOT / "supabase/tests/fixtures/wf06_two_user_canary_setup.sql"
CLEANUP_VERIFY_SQL = ROOT / "supabase/tests/fixtures/wf06_two_user_canary_verify_cleanup.sql"

sys.path.insert(0, str(ROOT / "scripts"))
import wf06_positive_rls_canary as canary  # noqa: E402


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=True, cwd=ROOT)


def load_project_keys() -> tuple[str, str]:
    completed = run_cli(
        [
            "supabase",
            "projects",
            "api-keys",
            "--project-ref",
            PROJECT_REF,
            "--reveal",
            "--output",
            "json",
        ]
    )
    payload = json.loads(completed.stdout)
    service = next((item.get("api_key") for item in payload if item.get("name") == "service_role"), None)
    anon = next((item.get("api_key") for item in payload if item.get("name") == "anon"), None)
    if not service or not anon:
        raise RuntimeError("Không tìm thấy legacy service_role/anon key; dừng fail-closed.")
    return service, anon


def request_json(
    method: str,
    url: str,
    apikey: str,
    body: dict[str, Any] | None = None,
) -> Any:
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=raw,
        method=method,
        headers={
            "apikey": apikey,
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8")
        raise RuntimeError(f"Supabase Auth HTTP {error.code}: {response_body[:300]}") from error
    return json.loads(response_body) if response_body else {}


def create_user(service_key: str, email: str, password: str, slot: str) -> str:
    payload = request_json(
        "POST",
        f"{SUPABASE_URL}/auth/v1/admin/users",
        service_key,
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "crave_canary": "wf06_rls_v1",
                "canary_slot": slot,
            },
        },
    )
    user_id = payload.get("id") or (payload.get("user") or {}).get("id")
    if not isinstance(user_id, str) or not user_id:
        raise RuntimeError("Admin create user không trả user id hợp lệ.")
    return user_id


def sign_in(anon_key: str, email: str, password: str) -> str:
    payload = request_json(
        "POST",
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        anon_key,
        {"email": email, "password": password},
    )
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Password sign-in không trả access token.")
    return token


def delete_user(service_key: str, user_id: str) -> None:
    request_json("DELETE", f"{SUPABASE_URL}/auth/v1/admin/users/{urllib.parse.quote(user_id)}", service_key)


def run_setup_sql() -> None:
    run_cli(["supabase", "db", "query", "--linked", "--file", str(SETUP_SQL)])


def verify_cleanup() -> None:
    run_cli(["supabase", "db", "query", "--linked", "--file", str(CLEANUP_VERIFY_SQL)])


def execute() -> int:
    service_key, anon_key = load_project_keys()
    password_a = secrets.token_urlsafe(32)
    password_b = secrets.token_urlsafe(32)
    created: list[str] = []
    evidence: dict[str, Any] = {
        "setup": False,
        "canary": None,
        "cleanup": False,
        "secrets_redacted": True,
    }
    exit_code = 1
    try:
        created.append(create_user(service_key, EMAIL_A, password_a, "A"))
        created.append(create_user(service_key, EMAIL_B, password_b, "B"))
        run_setup_sql()
        evidence["setup"] = True

        jwt_a = sign_in(anon_key, EMAIL_A, password_a)
        jwt_b = sign_in(anon_key, EMAIL_B, password_b)
        config = canary.CanaryConfig(True, True, MARKER_A, MARKER_B, "SOP")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            old_a = os.environ.get("CRAVE_WF06_JWT_A")
            old_b = os.environ.get("CRAVE_WF06_JWT_B")
            try:
                os.environ["CRAVE_WF06_JWT_A"] = jwt_a
                os.environ["CRAVE_WF06_JWT_B"] = jwt_b
                exit_code = canary.run_execute(config)
            finally:
                if old_a is None:
                    os.environ.pop("CRAVE_WF06_JWT_A", None)
                else:
                    os.environ["CRAVE_WF06_JWT_A"] = old_a
                if old_b is None:
                    os.environ.pop("CRAVE_WF06_JWT_B", None)
                else:
                    os.environ["CRAVE_WF06_JWT_B"] = old_b
        evidence["canary"] = json.loads(buffer.getvalue())
    except Exception as error:  # evidence is sanitized; secrets are never included in messages.
        evidence["operator_error"] = str(error)[:500]
        exit_code = 1
    finally:
        cleanup_errors: list[str] = []
        for user_id in reversed(created):
            try:
                delete_user(service_key, user_id)
            except Exception as error:
                cleanup_errors.append(str(error)[:300])
        try:
            verify_cleanup()
            evidence["cleanup"] = True
        except Exception as error:
            cleanup_errors.append(str(error)[:300])
        if cleanup_errors:
            evidence["cleanup_errors"] = cleanup_errors
            exit_code = 1
        service_key = ""
        anon_key = ""
        password_a = ""
        password_b = ""

    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return exit_code


def dry_run() -> int:
    print(
        json.dumps(
            {
                "mode": "dry-run",
                "network_requests": 0,
                "subprocess_calls": 0,
                "planned_auth_users": 2,
                "planned_profiles": 2,
                "planned_document_access_rows": 2,
                "app_role_assignments": 0,
                "markers": [MARKER_A, MARKER_B],
                "canary_cases": 6,
                "cleanup": "DELETE 2 Auth users; FK cascade profiles/access; verify zero residue",
                "secrets": "memory-only; never printed or persisted",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--i-understand-live-user-and-data-mutation", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.execute:
        if not args.i_understand_live_user_and_data_mutation:
            raise SystemExit("--execute requires --i-understand-live-user-and-data-mutation and exact approval")
        return execute()
    return dry_run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
