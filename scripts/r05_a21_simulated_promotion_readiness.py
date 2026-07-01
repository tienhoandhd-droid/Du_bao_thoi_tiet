#!/usr/bin/env python3
"""Run a local-only simulated positive path for the R05-A20 promotion gate.

This operator intentionally creates simulated owner approvals and simulated PDF
fixtures under R05-A21-specific work paths. It proves the gate mechanics can
reach READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN, but it never creates or
modifies the real corrected corpus path and never closes P0 blockers.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from r05_a20_owner_promotion_gate import (
    DECISION_FIELDS,
    PROMOTE_DECISION,
    REVIEWER_FIELD_BY_DECISION,
    build_report as build_a20_report,
    build_template_rows,
    load_a19_report,
    sha256_file,
    write_plan,
)
from r05_authoritative_corpus_intake import REQUIRED_CODES


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_A19_REPORT = ROOT / "work/r05_a19_controlled_draft_corpus_hash_parse_report.json"
DEFAULT_PLAN = ROOT / "work/r05_a21_simulated_owner_promotion_plan.csv"
DEFAULT_CORPUS = ROOT / "work/r05_a21_simulated_corrected_corpus"
DEFAULT_A20_OUTPUT = ROOT / "work/r05_a21_simulated_a20_gate_report.json"
DEFAULT_REPORT = ROOT / "work/r05_a21_simulated_promotion_readiness_report.json"
REAL_CORRECTED_CORPUS = ROOT / "work/r05_authoritative_corpus"

SIMULATED_REVIEWERS = {
    "technical_sme_decision": "Nguyen Van SME",
    "qa_gmp_decision": "Tran Thi QA",
    "data_integrity_decision": "Le Van Data Integrity",
    "license_owner_decision": "Pham Thi License Owner",
    "document_owner_decision": "Hoang Van Document Owner",
    "source_control_decision": "Do Thi Source Control",
}
SIMULATED_REVIEWED_AT = "2026-06-30T12:36:23+07:00"


def write_simulated_pdf(path: Path, document_code: str, document_title: str) -> None:
    payload = "\n".join([
        "%PDF-1.7",
        "% R05-A21 SIMULATED_ONLY_NOT_AUTHORITATIVE",
        f"1 0 obj << /Type /Catalog /Pages 2 0 R /CRAVECode ({document_code}) >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj",
        f"% Simulated corrected corpus fixture for {document_code}: {document_title}",
        "% This is not owner-approved GMP evidence and must not be imported.",
        "trailer << /Root 1 0 R >>",
        "%%EOF",
        "",
    ]).encode("utf-8")
    path.write_bytes(payload)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_simulated_plan_and_corpus(a19_report_path: Path, plan_path: Path, corpus_dir: Path) -> dict[str, Any]:
    a19_report = load_a19_report(a19_report_path)
    template_rows = build_template_rows(a19_report)
    write_plan(plan_path, template_rows)

    corpus_dir.mkdir(parents=True, exist_ok=True)
    for stale_file in corpus_dir.rglob("*"):
        if stale_file.is_file():
            stale_file.unlink()

    rows = read_csv(plan_path)
    record_by_code = {record["document_code"]: record for record in a19_report["records"]}
    pdf_records: list[dict[str, Any]] = []

    for row in rows:
        code = row["document_code"]
        source_record = record_by_code[code]
        file_name = f"{code}_SIMULATED_CORRECTED.pdf"
        pdf_path = corpus_dir / file_name
        write_simulated_pdf(pdf_path, code, source_record["document_title"])
        digest = sha256_file(pdf_path)

        for decision_field in DECISION_FIELDS:
            row[decision_field] = "APPROVED"
            reviewer_field, reviewed_at_field = REVIEWER_FIELD_BY_DECISION[decision_field]
            row[reviewer_field] = SIMULATED_REVIEWERS[decision_field]
            row[reviewed_at_field] = SIMULATED_REVIEWED_AT

        row["corrected_corpus_file_name"] = file_name
        row["corrected_corpus_sha256"] = digest
        row["promotion_decision"] = PROMOTE_DECISION
        row["promotion_notes"] = (
            "SIMULATED_ONLY_NOT_AUTHORITATIVE: local positive-path fixture; "
            "not a real GMP approval and not eligible for import."
        )
        pdf_records.append({
            "document_code": code,
            "file_name": file_name,
            "sha256": digest,
            "size_bytes": pdf_path.stat().st_size,
        })

    write_csv(plan_path, rows)
    return {
        "plan_path": str(plan_path),
        "plan_sha256": sha256_file(plan_path),
        "corpus_dir": str(corpus_dir),
        "pdf_records": sorted(pdf_records, key=lambda record: REQUIRED_CODES.index(record["document_code"])),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    simulation = build_simulated_plan_and_corpus(args.a19_report, args.review_plan, args.corpus_dir)
    a20_report = build_a20_report(
        args.a19_report,
        args.review_plan,
        args.corpus_dir,
        args.a20_output,
        write_template=False,
    )
    if a20_report["decision"] != "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN":
        raise RuntimeError(
            "Simulated A20 positive path did not reach READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN: "
            + a20_report["decision"]
        )

    report = {
        "schema_version": 1,
        "rhythm": "R05-A21",
        "ok": True,
        "decision": "SIMULATED_READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN",
        "simulation_only": True,
        "authoritative_effect": "DENY",
        "production_import_allowed": False,
        "retrieval_enablement_allowed": False,
        "real_corrected_corpus_path": str(REAL_CORRECTED_CORPUS),
        "real_corrected_corpus_exists": REAL_CORRECTED_CORPUS.exists(),
        "simulation": simulation,
        "a20_gate_result": {
            "path": str(args.a20_output),
            "sha256": sha256_file(args.a20_output),
            "decision": a20_report["decision"],
            "ok": a20_report["ok"],
            "promotion_plan_summary": a20_report["promotion_plan"]["summary"],
            "corrected_corpus": {
                "decision": a20_report["corrected_corpus"]["decision"],
                "ok": a20_report["corrected_corpus"]["ok"],
                "record_count": len(a20_report["corrected_corpus"]["records"]),
            },
        },
        "quality_controls": {
            "simulation_label_required": True,
            "real_owner_approval_claim": False,
            "real_authoritative_corpus_mutation": False,
            "real_work_r05_authoritative_corpus_mutation": False,
            "supabase_write": False,
            "n8n_operation": False,
            "git_remote": False,
        },
        "blockers": {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "next_step": (
            "Replace simulated fixtures with real owner-approved corpus/mapping, "
            "then run A20/A21-equivalent validation before requesting live hash/parse approval."
        ),
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a19-report", type=Path, default=DEFAULT_A19_REPORT)
    parser.add_argument("--review-plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--a20-output", type=Path, default=DEFAULT_A20_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(args)
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "simulation_only": report["simulation_only"],
        "a20_gate_decision": report["a20_gate_result"]["decision"],
        "real_corrected_corpus_exists": report["real_corrected_corpus_exists"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
