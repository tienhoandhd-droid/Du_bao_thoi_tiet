#!/usr/bin/env python3
"""CRAVE — Eval claim-verification qua webhook MoA trên bộ golden claims.

Chạy từng golden claim qua `crave-verify-moa`, chấm:
  - verdict_match : verdict ∈ expected_verdict
  - citation_ok   : có/không citation đúng kỳ vọng (expect_citation)
  - refusal_ok    : verdict 'insufficient' khớp expect_refusal (no-source refusal)
Tổng hợp tỉ lệ. KHÔNG chế số — chỉ báo đúng kết quả thật.

Chạy: ./.venv-scan/bin/python scripts/ingest/crave_eval_claims.py \
        eval/datasets/crave_golden_claims_lamsafe.jsonl [--url ...]
JWT (nếu webhook bật auth): env CRAVE_AL_JWT hoặc CRAVE_AL_EMAIL/PASSWORD.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

SUPABASE_URL = "https://bdttccztjtrcaztjgkot.supabase.co"
ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkdHRjY3p0anRyY2F6dGpna290Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI0Nzc3MDAsImV4cCI6MjA5ODA1MzcwMH0."
        "27_xCRuqqW1wUGtLzMYac0YFlG8aOMO5Mem5LZCbZI8")
DEFAULT_URL = "https://n8n.cpc1hn.com/webhook/crave-verify-moa"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
USER_ID = "08d0572c-9368-4034-bb26-ab1c88bd9e04"


def get_jwt() -> str | None:
    if os.environ.get("CRAVE_AL_JWT"):
        return os.environ["CRAVE_AL_JWT"].strip()
    email, pw = os.environ.get("CRAVE_AL_EMAIL"), os.environ.get("CRAVE_AL_PASSWORD")
    if not (email and pw):
        return None
    req = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        data=json.dumps({"email": email, "password": pw}).encode(), method="POST",
        headers={"Content-Type": "application/json", "apikey": ANON, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("access_token")
    except urllib.error.HTTPError:
        return None


def call_moa(url: str, question: str, jwt: str | None) -> dict:
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    req = urllib.request.Request(
        url, data=json.dumps({"question": question, "user_id": USER_ID}).encode(),
        method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()[:200]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", type=Path, default=Path("eval/reports/crave_claims_eval_latest.json"))
    args = ap.parse_args()

    claims = [json.loads(l) for l in args.dataset.read_text(encoding="utf-8").splitlines() if l.strip()]
    jwt = get_jwt()
    rows, vmatch, cite_ok, refuse_ok, errors = [], 0, 0, 0, 0
    for c in claims:
        resp = call_moa(args.url, c["question_vi"], jwt)
        if "_http_error" in resp:
            errors += 1
            rows.append({"id": c["id"], "error": resp})
            print(f"{c['id']}: ERROR HTTP {resp['_http_error']} {resp['_body']}")
            continue
        verdict = resp.get("verdict")
        citations = resp.get("citations") or resp.get("support") or []
        has_cite = len(citations) > 0
        vm = verdict in c["expected_verdict"]
        cm = has_cite == bool(c["expect_citation"])
        rm = (verdict == "insufficient") == bool(c["expect_refusal"])
        vmatch += vm; cite_ok += cm; refuse_ok += rm
        rows.append({"id": c["id"], "verdict": verdict, "confidence": resp.get("confidence"),
                     "verdict_match": vm, "citation_ok": cm, "refusal_ok": rm,
                     "n_citations": len(citations), "requires_human_signoff": resp.get("requires_human_signoff")})
        print(f"{c['id']}: verdict={verdict} conf={resp.get('confidence')} "
              f"vmatch={'Y' if vm else 'N'} cite_ok={'Y' if cm else 'N'} refuse_ok={'Y' if rm else 'N'} "
              f"cites={len(citations)}")

    n = len(claims)
    scored = n - errors
    summary = {
        "dataset": str(args.dataset), "n_claims": n, "errors": errors,
        "verdict_match_rate": round(vmatch / scored, 4) if scored else None,
        "citation_ok_rate": round(cite_ok / scored, 4) if scored else None,
        "refusal_ok_rate": round(refuse_ok / scored, 4) if scored else None,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(f"verdict_match={summary['verdict_match_rate']} citation_ok={summary['citation_ok_rate']} "
          f"refusal_ok={summary['refusal_ok_rate']} (scored {scored}/{n}, errors {errors})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
