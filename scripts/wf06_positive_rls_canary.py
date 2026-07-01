#!/usr/bin/env python3
"""WF-06 positive user-JWT/two-user RLS canary runner.

Default mode is dry-run and performs no network request. Production webhook reads
must be explicitly approved before running this script with --execute.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


ENDPOINT = "https://n8n.cpc1hn.com/webhook/search-docs"
ALLOWED_ORIGIN = "https://tienhoandhd-droid.github.io"
CLIENT_USER_AGENT = "CRAVE-WF06-Canary/1.0"
TIMEOUT_SECONDS = 15
DOCUMENT_ALLOWLIST = {
    "id",
    "document_group_id",
    "document_code",
    "document_title",
    "document_type",
    "language_code",
    "source_type",
    "version",
    "status",
    "approved_for_ai_use",
    "translation_status",
    "is_ai_translated",
    "owner_department",
    "equipment_type",
    "equipment_code",
    "file_name",
    "file_hash",
    "page_count",
    "chunk_count",
    "uploaded_at",
    "reviewed_at",
    "approved_at",
    "effective_date",
}
FORBIDDEN_FIELDS = {
    "content",
    "embedding",
    "file_content",
    "service_role_key",
    "jwt",
    "search_sql",
    "count_sql",
}


@dataclass(frozen=True)
class CanaryConfig:
    jwt_a_present: bool
    jwt_b_present: bool
    keyword_a_only: str
    keyword_b_only: str
    positive_keyword: str


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Thiếu biến môi trường bắt buộc: {name}")
    return value


def load_config(require_jwts: bool) -> CanaryConfig:
    if require_jwts:
        env_required("CRAVE_WF06_JWT_A")
        env_required("CRAVE_WF06_JWT_B")
    keyword_a = env_required("CRAVE_WF06_CANARY_A_ONLY_KEYWORD")
    keyword_b = env_required("CRAVE_WF06_CANARY_B_ONLY_KEYWORD")
    return CanaryConfig(
        jwt_a_present=bool(os.environ.get("CRAVE_WF06_JWT_A", "").strip()),
        jwt_b_present=bool(os.environ.get("CRAVE_WF06_JWT_B", "").strip()),
        keyword_a_only=keyword_a,
        keyword_b_only=keyword_b,
        positive_keyword=os.environ.get("CRAVE_WF06_POSITIVE_KEYWORD", "SOP").strip() or "SOP",
    )


def post_webhook(jwt: str, body: dict[str, Any], origin: str = ALLOWED_ORIGIN) -> tuple[int, dict[str, str], Any]:
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": origin,
            "Authorization": f"Bearer {jwt}",
            "User-Agent": CLIENT_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            headers = {key.lower(): value for key, value in response.headers.items()}
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status = error.code
        headers = {key.lower(): value for key, value in error.headers.items()}
        raw_body = error.read().decode("utf-8")
    try:
        parsed_body: Any = json.loads(raw_body) if raw_body else None
    except json.JSONDecodeError:
        parsed_body = {"_non_json_body": raw_body[:200]}
    return status, headers, parsed_body


def assert_success_response(name: str, status: int, headers: dict[str, str], body: Any) -> list[str]:
    failures: list[str] = []
    if status != 200:
        failures.append(f"{name}: expected HTTP 200, got {status}")
    if headers.get("access-control-allow-origin") != ALLOWED_ORIGIN:
        failures.append(f"{name}: CORS allow-origin mismatch")
    if not isinstance(body, dict) or body.get("success") is not True:
        failures.append(f"{name}: body.success is not true")
        return failures
    if not isinstance(body.get("documents"), list):
        failures.append(f"{name}: documents is not a list")
        return failures
    for index, document in enumerate(body["documents"]):
        if not isinstance(document, dict):
            failures.append(f"{name}: documents[{index}] is not an object")
            continue
        extra_fields = set(document) - DOCUMENT_ALLOWLIST
        forbidden = set(document) & FORBIDDEN_FIELDS
        if extra_fields:
            failures.append(f"{name}: documents[{index}] has non-allowlisted fields {sorted(extra_fields)}")
        if forbidden:
            failures.append(f"{name}: documents[{index}] has forbidden fields {sorted(forbidden)}")
    for field in ("total_count", "limit", "offset"):
        # bool là subclass của int trong Python; dùng type chính xác để payload
        # JSON true/false không thể giả mạo bộ đếm và tạo false PASS ở gate RLS.
        if type(body.get(field)) is not int:
            failures.append(f"{name}: {field} is not an integer")
    return failures


def total_count(body: Any) -> int | None:
    if isinstance(body, dict) and type(body.get("total_count")) is int:
        return body["total_count"]
    return None


def sanitized_error_text(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    for key in ("error", "message", "_non_json_body"):
        value = body.get(key)
        if isinstance(value, str) and value:
            return value[:160]
    return None


def run_execute(config: CanaryConfig) -> int:
    jwt_a = env_required("CRAVE_WF06_JWT_A")
    jwt_b = env_required("CRAVE_WF06_JWT_B")
    cases = [
        ("user_a_positive", jwt_a, {"keyword": config.positive_keyword, "limit": 5}, "success"),
        ("user_b_positive", jwt_b, {"keyword": config.positive_keyword, "limit": 5}, "success"),
        ("user_a_can_read_a_marker", jwt_a, {"keyword": config.keyword_a_only, "limit": 20}, "nonzero"),
        ("user_b_can_read_b_marker", jwt_b, {"keyword": config.keyword_b_only, "limit": 20}, "nonzero"),
        ("user_a_cannot_read_b_marker", jwt_a, {"keyword": config.keyword_b_only, "limit": 20}, "zero"),
        ("user_b_cannot_read_a_marker", jwt_b, {"keyword": config.keyword_a_only, "limit": 20}, "zero"),
    ]
    failures: list[str] = []
    evidence: list[dict[str, Any]] = []
    for name, jwt, request_body, expectation in cases:
        status, headers, body = post_webhook(jwt, request_body)
        case_failures = assert_success_response(name, status, headers, body)
        if expectation == "nonzero" and (total_count(body) is None or total_count(body) <= 0):
            case_failures.append(f"{name}: expected total_count>0, got {total_count(body)}")
        if expectation == "zero" and total_count(body) != 0:
            case_failures.append(f"{name}: expected total_count=0, got {total_count(body)}")
        failures.extend(case_failures)
        evidence.append(
            {
                "case": name,
                "http_status": status,
                "cors_ok": headers.get("access-control-allow-origin") == ALLOWED_ORIGIN,
                "success": isinstance(body, dict) and body.get("success") is True,
                "total_count": total_count(body),
                "documents_count": len(body.get("documents", [])) if isinstance(body, dict) else None,
                "response_error": sanitized_error_text(body),
            }
        )
    print(json.dumps({"endpoint": ENDPOINT, "evidence": evidence, "failures": failures}, indent=2, ensure_ascii=False))
    return 1 if failures else 0


def run_dry_run(config: CanaryConfig) -> int:
    summary = {
        "mode": "dry-run",
        "network_requests": 0,
        "endpoint": ENDPOINT,
        "allowed_origin": ALLOWED_ORIGIN,
        "jwt_a_present": config.jwt_a_present,
        "jwt_b_present": config.jwt_b_present,
        "canary_keywords_present": bool(config.keyword_a_only and config.keyword_b_only),
        "planned_cases": [
            "user_a_positive expects HTTP 200 and allowlisted response",
            "user_b_positive expects HTTP 200 and allowlisted response",
            "user_a_can_read_a_marker expects HTTP 200 and total_count>0",
            "user_b_can_read_b_marker expects HTTP 200 and total_count>0",
            "user_a_cannot_read_b_marker expects HTTP 200 and total_count=0",
            "user_b_cannot_read_a_marker expects HTTP 200 and total_count=0",
        ],
        "redaction": "JWT values are never printed or written by this runner.",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate local inputs only; default.")
    mode.add_argument("--execute", action="store_true", help="Call the production WF-06 webhook.")
    parser.add_argument(
        "--i-understand-production-read",
        action="store_true",
        help="Required with --execute after explicit user approval.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    executing = bool(args.execute)
    if executing and not args.i_understand_production_read:
        raise SystemExit("--execute requires --i-understand-production-read and prior approval")
    config = load_config(require_jwts=executing)
    if executing:
        return run_execute(config)
    return run_dry_run(config)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
