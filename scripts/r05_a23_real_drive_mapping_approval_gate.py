#!/usr/bin/env python3
"""Validate real owner-confirmed Drive IDs before controlled hash/parse.

R05-A23 is local-only. It does not download Drive binaries, call Supabase,
execute n8n, mutate workflow state, or touch Git remote. It closes the simulated
R05-A22 lane by requiring a real 12-row owner-confirmed mapping before the next
approval can even be requested.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from r05_authoritative_corpus_intake import (
    AUTHORITATIVE_STATUS,
    ID_COLUMNS,
    MIME_COLUMNS,
    NAME_COLUMNS,
    REQUIRED_CODES,
    STATUS_COLUMNS,
    first_present,
    is_placeholder,
    sha256_file,
    validate_mapping_csv,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REAL_MAPPING = ROOT / "work/r05_authoritative_12_file_mapping.csv"
DEFAULT_SIMULATED_MAPPING = ROOT / "work/r05_a22_simulated_authoritative_drive_mapping.csv"
DEFAULT_REQUIRED_TEMPLATE = ROOT / "work/r05_a23_owner_confirmed_drive_mapping_required.csv"
DEFAULT_APPROVAL_REQUEST = ROOT / "work/r05_a23_controlled_download_hash_parse_approval_request.md"
DEFAULT_OUTPUT = ROOT / "work/r05_a23_real_drive_mapping_approval_gate_report.json"

GOOGLE_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
SYNTHETIC_ID_MARKERS = (
    "SIMULATED",
    "NOT_REAL",
    "PLACEHOLDER",
    "REPLACE_WITH",
    "DUMMY",
    "FAKE",
)

REQUIRED_TEMPLATE_FIELDS = [
    "document_code",
    "drive_file_id",
    "status",
    "file_name",
    "mime_type",
    "owner_confirmation",
    "owner_confirmed_at_utc",
    "owner_reviewer",
    "notes",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def synthetic_markers_for_id(drive_file_id: str) -> list[str]:
    normalized = drive_file_id.upper()
    return [marker for marker in SYNTHETIC_ID_MARKERS if marker in normalized]


def valid_drive_id_format(drive_file_id: str) -> bool:
    return bool(GOOGLE_DRIVE_ID_RE.fullmatch(drive_file_id))


def summarize_mapping(path: Path) -> dict[str, Any]:
    rows = read_rows(path)
    intake = validate_mapping_csv(path).as_report() if path.exists() else {
        "ok": False,
        "decision": "FAIL_CLOSED",
        "mode": "mapping_csv",
        "record_count": 0,
        "records": [],
        "errors": [f"Mapping CSV not found: {path}"],
        "warnings": [],
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }

    drive_ids: list[str] = []
    statuses: list[str] = []
    file_names: list[str] = []
    mime_types: list[str] = []
    synthetic_rows: list[dict[str, Any]] = []
    invalid_format_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=2):
        code = (row.get("document_code") or "").strip()
        drive_file_id = first_present(row, ID_COLUMNS)
        status = first_present(row, STATUS_COLUMNS)
        file_name = first_present(row, NAME_COLUMNS)
        mime_type = first_present(row, MIME_COLUMNS)
        drive_ids.append(drive_file_id)
        statuses.append(status)
        file_names.append(file_name)
        mime_types.append(mime_type)

        if drive_file_id and not is_placeholder(drive_file_id):
            markers = synthetic_markers_for_id(drive_file_id)
            if markers:
                synthetic_rows.append({
                    "source_row": index,
                    "document_code": code,
                    "drive_file_id": drive_file_id,
                    "markers": markers,
                })
            if not valid_drive_id_format(drive_file_id):
                invalid_format_rows.append({
                    "source_row": index,
                    "document_code": code,
                    "drive_file_id": drive_file_id,
                })

    concrete_ids = [item for item in drive_ids if item and not is_placeholder(item)]
    duplicate_ids = sorted({item for item in concrete_ids if concrete_ids.count(item) > 1})
    authoritative_confirmed_count = sum(status.upper() == AUTHORITATIVE_STATUS for status in statuses)

    strict_errors: list[str] = []
    if synthetic_rows:
        strict_errors.append("Mapping contains simulated/synthetic Drive IDs.")
    if invalid_format_rows:
        strict_errors.append("Mapping contains Drive IDs outside the expected Google Drive ID character/length envelope.")
    if duplicate_ids:
        strict_errors.append("Mapping contains duplicate concrete Drive IDs.")

    strict_ok = bool(intake["ok"]) and not strict_errors
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "row_count": len(rows),
        "required_row_count": len(REQUIRED_CODES),
        "authoritative_confirmed_count": authoritative_confirmed_count,
        "concrete_drive_id_count": len(concrete_ids),
        "placeholder_drive_id_count": len(drive_ids) - len(concrete_ids),
        "pdf_file_name_count": sum(name.lower().endswith(".pdf") for name in file_names if name),
        "pdf_mime_count": sum(mime.lower() == "application/pdf" for mime in mime_types),
        "synthetic_drive_id_count": len(synthetic_rows),
        "invalid_drive_id_format_count": len(invalid_format_rows),
        "duplicate_concrete_drive_ids": duplicate_ids,
        "synthetic_rows": synthetic_rows,
        "invalid_format_rows": invalid_format_rows,
        "intake": {
            "ok": intake["ok"],
            "decision": intake["decision"],
            "record_count": intake["record_count"],
            "errors": intake["errors"],
            "warnings": intake["warnings"],
        },
        "strict_real_id_check": {
            "ok": strict_ok,
            "decision": "PASS" if strict_ok else "FAIL_CLOSED",
            "errors": strict_errors,
        },
    }


def write_required_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_TEMPLATE_FIELDS)
        writer.writeheader()
        for code in REQUIRED_CODES:
            writer.writerow({
                "document_code": code,
                "drive_file_id": "REPLACE_WITH_OWNER_CONFIRMED_DRIVE_FILE_ID",
                "status": "AWAITING_OWNER_CONFIRMED_DRIVE_ID",
                "file_name": f"{code}.pdf",
                "mime_type": "application/pdf",
                "owner_confirmation": "REQUIRED",
                "owner_confirmed_at_utc": "REQUIRED",
                "owner_reviewer": "REQUIRED",
                "notes": "Do not use simulated, sample, archive, folder or non-PDF IDs.",
            })


def approval_request_text(*, report: dict[str, Any]) -> str:
    mapping = report["inputs"]["real_mapping_csv"]
    usable = report["ok"]
    mapping_hash = mapping["sha256"] or "REQUIRED_AFTER_REAL_MAPPING_READY"
    readiness = report["decision"]
    prefix = (
        "STATUS: READY_TO_REQUEST_APPROVAL\n"
        if usable
        else "STATUS: NOT_READY_DO_NOT_APPROVE_YET\n"
    )
    guard = (
        "Guard: chi dung request nay sau khi "
        "`work/r05_a23_real_drive_mapping_approval_gate_report.json` co "
        "`decision = READY_FOR_CONTROLLED_DOWNLOAD_HASH_PARSE_APPROVAL`.\n"
    )
    exact_request = (
        "Toi duyet R05-A24: cho phep Codex chay controlled TKTL-only n8n "
        "Google Drive authoritative corpus download/hash/parse bang credential "
        "`ket noi drive`, chi dung 12 Drive file IDs owner-confirmed trong "
        f"`work/r05_authoritative_12_file_mapping.csv` (sha256 `{mapping_hash}`), "
        "workflow inactive/unpublished, one-file-per-execution/concurrency 1; "
        "duoc download binary tung PDF de lay byte_count, SHA-256, checksum neu "
        "Drive metadata co san, page_count, bounded text-layer/parse evidence, "
        "va bounded multi-engine OCR/table/figure evidence chi khi text-layer "
        "rong hoac phat hien bang/hinh theo contract R05-A06/A07/A08/A09; "
        "moi disagreement phai dua vao review candidate, khong auto-approve; "
        "khong Supabase write/import/indexing, khong OCR full toan bo neu chua "
        "can, khong chunk/embed, khong publish/archive/update production workflow, "
        "khong Git remote. Output chi ghi local vao "
        "`work/r05_a24_authoritative_download_hash_parse_report.json` va khong "
        "dong BLK-003/004 neu thieu/nham ma hoac reviewer evidence."
    )
    return (
        "# R05-A23 controlled download/hash/parse approval request\n\n"
        f"{prefix}\n"
        f"Current decision: `{readiness}`.\n\n"
        f"{guard}\n"
        "Exact approval text to paste only after the guard passes:\n\n"
        "```text\n"
        f"{exact_request}\n"
        "```\n"
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    write_required_template(args.required_template)
    real_mapping = summarize_mapping(args.real_mapping)
    simulated_mapping = summarize_mapping(args.simulated_mapping)

    ok = bool(real_mapping["strict_real_id_check"]["ok"])
    decision = (
        "READY_FOR_CONTROLLED_DOWNLOAD_HASH_PARSE_APPROVAL"
        if ok
        else "FAIL_CLOSED_REAL_DRIVE_IDS_REQUIRED"
    )

    report: dict[str, Any] = {
        "schema_version": 1,
        "rhythm": "R05-A23",
        "gate": "P0_REAL_OWNER_CONFIRMED_DRIVE_MAPPING_APPROVAL_GATE",
        "ok": ok,
        "decision": decision,
        "download_allowed_now": False,
        "download_allowed_after_fresh_approval": ok,
        "production_import_allowed": False,
        "citation_runtime_allowed": False,
        "agent_canary_allowed": False,
        "inputs": {
            "real_mapping_csv": real_mapping,
            "a22_simulated_mapping_csv": simulated_mapping,
            "required_template": {
                "path": str(args.required_template),
                "exists": args.required_template.exists(),
                "sha256": sha256_file(args.required_template),
                "row_count": len(REQUIRED_CODES),
            },
        },
        "quality_controls": {
            "required_document_codes": list(REQUIRED_CODES),
            "required_status": AUTHORITATIVE_STATUS,
            "required_mime_type": "application/pdf",
            "simulated_drive_ids_denied": True,
            "placeholder_drive_ids_denied": True,
            "duplicate_drive_ids_denied": True,
            "owner_confirmation_required": True,
            "fresh_n8n_approval_required_after_mapping_pass": True,
            "supabase_write_denied": True,
            "git_remote_denied": True,
        },
        "approval_request": {
            "path": str(args.approval_request),
            "status": "READY_TO_REQUEST_APPROVAL" if ok else "NOT_READY_DO_NOT_APPROVE_YET",
            "precondition": "A23 decision must be READY_FOR_CONTROLLED_DOWNLOAD_HASH_PARSE_APPROVAL.",
        },
        "blockers": {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "next_step": (
            "Ask for exact R05-A24 controlled n8n approval, then run one-file-per-execution download/hash/parse."
            if ok
            else "Replace placeholders/simulated IDs with 12 owner-confirmed Drive file IDs in the real mapping CSV, then rerun A23."
        ),
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }
    args.approval_request.parent.mkdir(parents=True, exist_ok=True)
    args.approval_request.write_text(approval_request_text(report=report), encoding="utf-8")
    write_json(args.output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-mapping", type=Path, default=DEFAULT_REAL_MAPPING)
    parser.add_argument("--simulated-mapping", type=Path, default=DEFAULT_SIMULATED_MAPPING)
    parser.add_argument("--required-template", type=Path, default=DEFAULT_REQUIRED_TEMPLATE)
    parser.add_argument("--approval-request", type=Path, default=DEFAULT_APPROVAL_REQUEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    report = build_report(parse_args())
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "real_mapping_concrete_ids": report["inputs"]["real_mapping_csv"]["concrete_drive_id_count"],
        "real_mapping_synthetic_ids": report["inputs"]["real_mapping_csv"]["synthetic_drive_id_count"],
        "a22_simulated_ids_rejected": report["inputs"]["a22_simulated_mapping_csv"]["synthetic_drive_id_count"],
        "approval_request_status": report["approval_request"]["status"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
