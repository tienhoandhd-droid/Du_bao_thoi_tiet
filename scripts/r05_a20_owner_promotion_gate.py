#!/usr/bin/env python3
"""Build and validate the R05-A20 per-document owner promotion gate.

This local-only operator creates a fillable owner-promotion plan from the
R05-A19 review corpus and validates whether every document has real human review
decisions before it can be considered for a corrected authoritative corpus path.
It never approves a document, copies a file into production, calls n8n, writes
Supabase, chunks, embeds, or enables retrieval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from r05_authoritative_corpus_intake import REQUIRED_CODES, validate_corpus_dir


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_A19_REPORT = ROOT / "work/r05_a19_controlled_draft_corpus_hash_parse_report.json"
DEFAULT_PLAN = ROOT / "work/r05_a20_owner_promotion_plan.csv"
DEFAULT_CORRECTED_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_REPORT = ROOT / "work/r05_a20_owner_promotion_gate_report.json"

APPROVED = "APPROVED"
PROMOTE_DECISION = "PROMOTE_TO_CORRECTED_CORPUS_PENDING_HASH_PARSE_PLAN"
DENY_DECISION = "DENY_UNTIL_ALL_REQUIRED_REVIEWS_PASS"
AI_REVIEWER_DENY_RE = re.compile(r"\b(codex|chatgpt|openai|gpt|artificial intelligence|ai)\b", re.I)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:$|[T\s])")

DECISION_FIELDS = (
    "technical_sme_decision",
    "qa_gmp_decision",
    "data_integrity_decision",
    "license_owner_decision",
    "document_owner_decision",
    "source_control_decision",
)
REVIEWER_FIELD_BY_DECISION = {
    "technical_sme_decision": ("technical_sme_name", "technical_sme_reviewed_at"),
    "qa_gmp_decision": ("qa_gmp_name", "qa_gmp_reviewed_at"),
    "data_integrity_decision": ("data_integrity_name", "data_integrity_reviewed_at"),
    "license_owner_decision": ("license_owner_name", "license_owner_reviewed_at"),
    "document_owner_decision": ("document_owner_name", "document_owner_reviewed_at"),
    "source_control_decision": ("source_control_name", "source_control_reviewed_at"),
}
PLAN_FIELDS = [
    "document_code",
    "document_title",
    "source_file_name",
    "source_artifact_status",
    "source_type",
    "source_sha256",
    "source_page_count",
    "source_sampled_text_char_count",
    "source_sampled_table_count",
    "source_figure_marker_count",
    "corrected_corpus_required",
    "corrected_corpus_file_name",
    "corrected_corpus_sha256",
    "technical_sme_decision",
    "technical_sme_name",
    "technical_sme_reviewed_at",
    "qa_gmp_decision",
    "qa_gmp_name",
    "qa_gmp_reviewed_at",
    "data_integrity_decision",
    "data_integrity_name",
    "data_integrity_reviewed_at",
    "license_owner_decision",
    "license_owner_name",
    "license_owner_reviewed_at",
    "document_owner_decision",
    "document_owner_name",
    "document_owner_reviewed_at",
    "source_control_decision",
    "source_control_name",
    "source_control_reviewed_at",
    "promotion_decision",
    "promotion_notes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_a19_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"R05-A19 report not found: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("rhythm") != "R05-A19":
        raise ValueError(f"Expected R05-A19 report, found {report.get('rhythm')!r}.")
    records = report.get("records") or []
    codes = {record.get("document_code") for record in records}
    if set(REQUIRED_CODES) != codes:
        raise ValueError("R05-A19 report does not contain exactly the required 12 document codes.")
    return report


def build_template_rows(a19_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    records = sorted(a19_report["records"], key=lambda record: REQUIRED_CODES.index(record["document_code"]))
    for record in records:
        rows.append({
            "document_code": record["document_code"],
            "document_title": record["document_title"],
            "source_file_name": record["file_name"],
            "source_artifact_status": record["artifact_status"],
            "source_type": record["source_type"],
            "source_sha256": record["sha256"],
            "source_page_count": record["page_count"],
            "source_sampled_text_char_count": record["sampled_text_char_count"],
            "source_sampled_table_count": record["sampled_table_count"],
            "source_figure_marker_count": record["figure_marker_count"],
            "corrected_corpus_required": "YES",
            "corrected_corpus_file_name": "",
            "corrected_corpus_sha256": "",
            "technical_sme_decision": "PENDING",
            "technical_sme_name": "",
            "technical_sme_reviewed_at": "",
            "qa_gmp_decision": "PENDING",
            "qa_gmp_name": "",
            "qa_gmp_reviewed_at": "",
            "data_integrity_decision": "PENDING",
            "data_integrity_name": "",
            "data_integrity_reviewed_at": "",
            "license_owner_decision": "PENDING",
            "license_owner_name": "",
            "license_owner_reviewed_at": "",
            "document_owner_decision": "PENDING",
            "document_owner_name": "",
            "document_owner_reviewed_at": "",
            "source_control_decision": "PENDING",
            "source_control_name": "",
            "source_control_reviewed_at": "",
            "promotion_decision": DENY_DECISION,
            "promotion_notes": "AI/Codex cannot approve GMP documents. Owner must create/confirm corrected corpus before promotion.",
        })
    return rows


def write_plan(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PLAN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_plan(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in PLAN_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Promotion plan missing required columns: " + ", ".join(missing) + ".")
        return list(reader)


def normalize(value: str | None) -> str:
    return (value or "").strip()


def is_ai_reviewer(name: str) -> bool:
    normalized = normalize(name)
    return bool(AI_REVIEWER_DENY_RE.search(normalized))


def validate_plan_rows(rows: list[dict[str, str]], a19_report: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    records_by_code = {record["document_code"]: record for record in a19_report["records"]}
    seen_codes: dict[str, int] = {}
    approved_count = 0

    for idx, row in enumerate(rows, start=2):
        code = normalize(row.get("document_code"))
        if code not in records_by_code:
            errors.append(f"Row {idx}: unexpected or missing document_code {code!r}.")
            continue

        seen_codes[code] = seen_codes.get(code, 0) + 1
        if seen_codes[code] > 1:
            errors.append(f"Row {idx}: duplicate document_code {code}.")

        source_record = records_by_code[code]
        if normalize(row.get("source_sha256")) != source_record["sha256"]:
            errors.append(f"Row {idx}: {code} source_sha256 does not match R05-A19 retained evidence.")
        if normalize(row.get("source_file_name")) != source_record["file_name"]:
            errors.append(f"Row {idx}: {code} source_file_name does not match R05-A19 retained evidence.")

        row_all_approved = True
        for decision_field in DECISION_FIELDS:
            decision = normalize(row.get(decision_field)).upper()
            reviewer_field, reviewed_at_field = REVIEWER_FIELD_BY_DECISION[decision_field]
            reviewer = normalize(row.get(reviewer_field))
            reviewed_at = normalize(row.get(reviewed_at_field))

            if decision != APPROVED:
                row_all_approved = False
                errors.append(f"Row {idx}: {code} {decision_field} must be {APPROVED!r}; found {decision!r}.")
            if not reviewer:
                row_all_approved = False
                errors.append(f"Row {idx}: {code} {reviewer_field} is required.")
            elif is_ai_reviewer(reviewer):
                row_all_approved = False
                errors.append(f"Row {idx}: {code} {reviewer_field} cannot be an AI/Codex/OpenAI reviewer.")
            if not DATE_RE.match(reviewed_at):
                row_all_approved = False
                errors.append(f"Row {idx}: {code} {reviewed_at_field} must start with an ISO date YYYY-MM-DD.")

        corrected_required = normalize(row.get("corrected_corpus_required")).upper()
        if corrected_required != "YES":
            row_all_approved = False
            errors.append(f"Row {idx}: {code} corrected_corpus_required must be 'YES'.")
        if normalize(row.get("promotion_decision")) != PROMOTE_DECISION:
            row_all_approved = False
            errors.append(
                f"Row {idx}: {code} promotion_decision must be {PROMOTE_DECISION!r} "
                "after all human reviews pass."
            )
        if not normalize(row.get("corrected_corpus_file_name")):
            row_all_approved = False
            errors.append(f"Row {idx}: {code} corrected_corpus_file_name is required before promotion.")
        if not normalize(row.get("corrected_corpus_sha256")):
            row_all_approved = False
            errors.append(f"Row {idx}: {code} corrected_corpus_sha256 is required before promotion.")

        if row_all_approved:
            approved_count += 1

    missing = sorted(set(REQUIRED_CODES) - set(seen_codes))
    if missing:
        errors.append("Promotion plan missing required document codes: " + ", ".join(missing) + ".")
    if len(rows) != len(REQUIRED_CODES):
        errors.append(f"Promotion plan must contain exactly 12 rows; found {len(rows)}.")

    if approved_count == 0:
        warnings.append("No document has a complete human-approved promotion row.")
    elif approved_count < len(REQUIRED_CODES):
        warnings.append(f"Only {approved_count}/12 documents have complete human-approved promotion rows.")

    summary = {
        "row_count": len(rows),
        "complete_human_approved_rows": approved_count,
        "required_rows": len(REQUIRED_CODES),
        "all_rows_complete": approved_count == len(REQUIRED_CODES),
    }
    return errors, warnings, summary


def validate_corrected_corpus(
    corrected_corpus_dir: Path,
    rows: list[dict[str, str]],
    plan_complete: bool,
) -> dict[str, Any]:
    if not corrected_corpus_dir.exists():
        return {
            "exists": False,
            "ok": False,
            "decision": "MISSING",
            "path": str(corrected_corpus_dir),
            "errors": [f"corrected corpus folder not found: {corrected_corpus_dir}"],
            "records": [],
        }

    intake = validate_corpus_dir(corrected_corpus_dir).as_report()
    corpus = {
        "exists": True,
        "ok": intake["ok"],
        "decision": intake["decision"],
        "path": str(corrected_corpus_dir),
        "errors": list(intake["errors"]),
        "records": intake["records"],
    }
    if not plan_complete or not intake["ok"]:
        return corpus

    planned_hash_by_code = {
        normalize(row["document_code"]): normalize(row["corrected_corpus_sha256"])
        for row in rows
    }
    planned_file_by_code = {
        normalize(row["document_code"]): normalize(row["corrected_corpus_file_name"])
        for row in rows
    }
    for record in intake["records"]:
        code = record["document_code"]
        if planned_hash_by_code[code] != record["sha256"]:
            corpus["ok"] = False
            corpus["decision"] = "FAIL_CLOSED"
            corpus["errors"].append(
                f"{code}: corrected_corpus_sha256 does not match actual corrected corpus binary."
            )
        if planned_file_by_code[code] != Path(record["relative_path"]).name:
            corpus["ok"] = False
            corpus["decision"] = "FAIL_CLOSED"
            corpus["errors"].append(
                f"{code}: corrected_corpus_file_name does not match actual corrected corpus file."
            )
    return corpus


def build_report(
    a19_report_path: Path,
    plan_path: Path,
    corrected_corpus_dir: Path,
    output_path: Path,
    write_template: bool,
) -> dict[str, Any]:
    a19_report = load_a19_report(a19_report_path)
    if write_template or not plan_path.exists():
        write_plan(plan_path, build_template_rows(a19_report))

    rows = read_plan(plan_path)
    plan_errors, plan_warnings, plan_summary = validate_plan_rows(rows, a19_report)
    plan_complete = not plan_errors and plan_summary["all_rows_complete"]
    corrected_corpus = validate_corrected_corpus(corrected_corpus_dir, rows, plan_complete)

    if plan_errors:
        decision = "FAIL_CLOSED_OWNER_APPROVAL_REQUIRED"
        ok = False
        next_step = "Human owner/SME/QA/data-integrity/license reviewers must complete and sign the per-document promotion plan."
    elif not corrected_corpus["exists"]:
        decision = "READY_FOR_CORRECTED_CORPUS_BUILD_PLAN"
        ok = True
        next_step = "Build or place corrected owner-approved PDFs, then rerun R05-A20."
    elif not corrected_corpus["ok"]:
        decision = "FAIL_CLOSED_CORRECTED_CORPUS_INVALID"
        ok = False
        next_step = "Fix the corrected corpus folder or plan hash/file-name linkage, then rerun R05-A20."
    else:
        decision = "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN"
        ok = True
        next_step = "Prepare a fresh exact n8n/Supabase live plan for controlled hash/parse/current-version linkage."

    report = {
        "schema_version": 1,
        "rhythm": "R05-A20",
        "ok": ok,
        "decision": decision,
        "gate": "P0_OWNER_PROMOTION_OR_CORRECTED_CORPUS",
        "a19_report": {
            "path": str(a19_report_path),
            "sha256": sha256_file(a19_report_path),
            "decision": a19_report.get("decision"),
            "document_count": a19_report.get("document_count"),
            "authoritative_confirmed_count": a19_report.get("authoritative_confirmed_count"),
        },
        "promotion_plan": {
            "path": str(plan_path),
            "sha256": sha256_file(plan_path),
            "write_template": write_template,
            "summary": plan_summary,
            "errors": plan_errors,
            "warnings": plan_warnings,
        },
        "corrected_corpus": corrected_corpus,
        "quality_controls": {
            "human_reviewer_required": True,
            "ai_codex_reviewer_denied": True,
            "all_six_review_decisions_required": list(DECISION_FIELDS),
            "corrected_corpus_required": True,
            "draft_marker_intake_rejection_inherited": True,
            "auto_approval": False,
        },
        "blockers": {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "next_step": next_step,
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a19-report", type=Path, default=DEFAULT_A19_REPORT)
    parser.add_argument("--review-plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--corrected-corpus-dir", type=Path, default=DEFAULT_CORRECTED_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-template", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(
        args.a19_report,
        args.review_plan,
        args.corrected_corpus_dir,
        args.output,
        args.write_template,
    )
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "promotion_plan": report["promotion_plan"]["summary"],
        "corrected_corpus_decision": report["corrected_corpus"]["decision"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
