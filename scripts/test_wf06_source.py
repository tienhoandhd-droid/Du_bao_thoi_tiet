#!/usr/bin/env python3
"""Kiểm contract source-only cho TKTL WF-06 R01-A03; không gọi live service."""

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / "n8n/workflows/TKTL-WF-06-document-search.json"
CONTRACT_PATH = ROOT / "n8n/workflow-contracts/document-search.json"
PAYLOAD_PATH = ROOT / "n8n/test-payloads/document-search.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_code_node(code: str, request: dict, verified_user: dict):
    harness = r"""
const code = JSON.parse(process.argv[1]);
const request = JSON.parse(process.argv[2]);
const verified = JSON.parse(process.argv[3]);
function $(name) {
  if (name === 'Webhook Search') return { first: () => ({ json: request }) };
  if (name === '🔐 Verify JWT') return { first: () => ({ json: verified }) };
  throw new Error('Unexpected node lookup: ' + name);
}
const result = new Function('$', code)($);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", harness, json.dumps(code), json.dumps(request), json.dumps(verified_user)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def run_format_node(code: str, rpc_payload: dict, filters: dict):
    harness = r"""
const code = JSON.parse(process.argv[1]);
const payload = JSON.parse(process.argv[2]);
const filters = JSON.parse(process.argv[3]);
function $(name) {
  if (name === 'Validate Request') return { first: () => ({ json: { filters_applied: filters } }) };
  throw new Error('Unexpected node lookup: ' + name);
}
const $input = { first: () => ({ json: payload }) };
const result = new Function('$', '$input', code)($, $input);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", harness, json.dumps(code), json.dumps(rpc_payload), json.dumps(filters)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


class WF06SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_json(WORKFLOW_PATH)
        cls.contract = load_json(CONTRACT_PATH)
        cls.payloads = load_json(PAYLOAD_PATH)
        cls.nodes = {node["name"]: node for node in cls.workflow["nodes"]}

    def test_identity_scope_and_graph(self):
        self.assertEqual(self.workflow["id"], "o4fuUanxRrD7qQoG")
        self.assertTrue(self.workflow["name"].startswith("TKTL WF-06"))
        self.assertEqual(len(self.nodes), len(self.workflow["nodes"]), "Tên node phải duy nhất")
        for source, outputs in self.workflow["connections"].items():
            self.assertIn(source, self.nodes)
            for branch in outputs["main"]:
                for edge in branch:
                    self.assertIn(edge["node"], self.nodes)

    def test_no_owner_postgres_or_dynamic_sql(self):
        serialized = json.dumps(self.workflow, ensure_ascii=False)
        self.assertNotIn("n8n-nodes-base.postgres", serialized)
        self.assertNotIn("GMP-check", serialized)
        self.assertNotIn("executeQuery", serialized)
        self.assertNotIn("search_sql", serialized)
        self.assertNotIn("count_sql", serialized)
        self.assertEqual(self.workflow["_crave_meta"]["credentialBindings"], [])
        self.assertFalse(any("credentials" in node for node in self.workflow["nodes"]))

    def test_verify_jwt_contract_unchanged(self):
        node = self.nodes["🔐 Verify JWT"]
        self.assertEqual(node["parameters"]["url"], "https://bdttccztjtrcaztjgkot.supabase.co/auth/v1/user")
        self.assertEqual(node["onError"], "continueErrorOutput")
        headers = {item["name"]: item["value"] for item in node["parameters"]["headerParameters"]["parameters"]}
        self.assertEqual(headers["Authorization"], "={{ $json.headers.authorization }}")
        self.assertEqual(headers["apikey"], "__REDACTED_SUPABASE_ANON_KEY__")

    def test_postgrest_user_jwt_contract(self):
        node = self.nodes["PostgREST: search_documents_v1"]
        self.assertEqual(node["type"], "n8n-nodes-base.httpRequest")
        self.assertEqual(node["parameters"]["method"], "POST")
        self.assertEqual(
            node["parameters"]["url"],
            "https://bdttccztjtrcaztjgkot.supabase.co/rest/v1/rpc/search_documents_v1",
        )
        self.assertEqual(node["onError"], "continueErrorOutput")
        headers = {item["name"]: item["value"] for item in node["parameters"]["headerParameters"]["parameters"]}
        self.assertIn("Validate Request", headers["Authorization"])
        self.assertEqual(headers["apikey"], "__REDACTED_SUPABASE_ANON_KEY__")
        self.assertIn("rpc_body", node["parameters"]["jsonBody"])

    def test_cors_decision(self):
        origin = self.nodes["Webhook Search"]["parameters"]["options"]["allowedOrigins"]
        self.assertEqual(origin, "https://tienhoandhd-droid.github.io")
        self.assertNotEqual(origin, "*")
        self.assertEqual(origin, self.contract["endpoint"]["cors_allowed_origin"])

    def test_validate_node_runtime_synthetic(self):
        code = self.nodes["Validate Request"]["parameters"]["jsCode"]
        self.assertNotIn("Buffer.from", code)
        self.assertNotIn("token.split", code)
        verified = {"id": "11111111-1111-4111-8111-111111111111", "email": "synthetic@example.invalid"}

        valid = run_code_node(
            code,
            {"headers": {"authorization": "Bearer synthetic.valid.jwt"}, "body": {"keyword": "SOP", "limit": 10}},
            verified,
        )[0]["json"]
        self.assertFalse(valid["error"])
        self.assertEqual(valid["rpc_body"]["p_keyword"], "SOP")
        self.assertEqual(valid["rpc_body"]["p_limit"], 10)
        self.assertNotIn("user_id", valid["rpc_body"])

        missing_bearer = run_code_node(code, {"headers": {}, "body": {}}, verified)[0]["json"]
        self.assertEqual(missing_bearer["status"], 401)

        invalid_enum = run_code_node(
            code,
            {"headers": {"authorization": "Bearer synthetic.valid.jwt"}, "body": {"document_type": "sop');select 1;--"}},
            verified,
        )[0]["json"]
        self.assertEqual(invalid_enum["status"], 400)

        invalid_limit = run_code_node(
            code,
            {"headers": {"authorization": "Bearer synthetic.valid.jwt"}, "body": {"limit": 101}},
            verified,
        )[0]["json"]
        self.assertEqual(invalid_limit["status"], 400)

        keyword = "%' OR true --"
        injection_literal = run_code_node(
            code,
            {"headers": {"authorization": "Bearer synthetic.valid.jwt"}, "body": {"keyword": keyword}},
            verified,
        )[0]["json"]
        self.assertEqual(injection_literal["rpc_body"]["p_keyword"], keyword)
        self.assertNotIn("sql", injection_literal)

    def test_response_allowlist_runtime_synthetic(self):
        code = self.nodes["Format Results"]["parameters"]["jsCode"]
        allowed = self.contract["response"]["document_allowlist"]
        source_document = {field: "synthetic" for field in allowed}
        source_document.update({"content": "forbidden", "embedding": [1, 2], "service_role_key": "forbidden"})
        result = run_format_node(
            code,
            {"documents": [source_document], "total_count": 1, "limit": 50, "offset": 0},
            {"p_limit": 50, "p_offset": 0},
        )[0]["json"]
        self.assertFalse(result["error"])
        self.assertEqual(set(result["documents"][0]), set(allowed))
        self.assertNotIn("content", result["documents"][0])
        self.assertNotIn("embedding", result["documents"][0])
        self.assertNotIn("service_role_key", result["documents"][0])

    def test_required_negative_payload_matrix(self):
        case_ids = {case["id"] for case in self.payloads["cases"]}
        required = {
            "positive_default", "missing_jwt", "invalid_jwt", "invalid_enum_format",
            "invalid_enum_value", "keyword_injection_literal", "limit_zero",
            "limit_above_max", "offset_negative", "nonprivileged_superseded",
            "privileged_superseded", "two_user_rls_leakage", "cors_allowed_origin",
            "cors_denied_origin",
        }
        self.assertTrue(required.issubset(case_ids))


if __name__ == "__main__":
    unittest.main()
