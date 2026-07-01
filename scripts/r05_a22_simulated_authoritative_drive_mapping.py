#!/usr/bin/env python3
"""Create a simulated real-shape authoritative Drive mapping and validate it.

This local-only operator exercises the mapping-csv path of the authoritative
intake gate. It creates a realistic-looking but explicitly simulated mapping
under R05-A22-specific work paths. It must not overwrite the real mapping
template, download Drive binaries, write Supabase, execute n8n, or close P0
blockers.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from r05_authoritative_corpus_intake import REQUIRED_CODES, sha256_file, validate_mapping_csv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "work/r05_a22_simulated_authoritative_drive_mapping.csv"
DEFAULT_INTAKE_REPORT = ROOT / "work/r05_a22_simulated_authoritative_drive_mapping_intake_report.json"
DEFAULT_REPORT = ROOT / "work/r05_a22_simulated_authoritative_drive_mapping_report.json"
REAL_MAPPING = ROOT / "work/r05_authoritative_12_file_mapping.csv"
REAL_CORRECTED_CORPUS = ROOT / "work/r05_authoritative_corpus"

FIELDNAMES = [
    "document_code",
    "drive_file_id",
    "status",
    "file_name",
    "mime_type",
    "simulation_notice",
    "source_path_hint",
]


def simulated_drive_id(index: int, code: str) -> str:
    normalized = code.replace("-", "")
    return f"SIMULATED_DRIVE_ID_{index:02d}_{normalized}_NOT_REAL_20260630"


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, code in enumerate(REQUIRED_CODES, start=1):
        rows.append({
            "document_code": code,
            "drive_file_id": simulated_drive_id(index, code),
            "status": "AUTHORITATIVE_CONFIRMED",
            "file_name": f"{code}_AUTHORITATIVE_SIMULATED.pdf",
            "mime_type": "application/pdf",
            "simulation_notice": "SIMULATED_ONLY_NOT_AUTHORITATIVE_DO_NOT_DOWNLOAD_OR_IMPORT",
            "source_path_hint": "/SIMULATED_DRIVE_AUTHORITATIVE_CORPUS",
        })
    return rows


def write_mapping(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.mapping_csv.resolve() == REAL_MAPPING.resolve():
        raise ValueError("Refusing to write simulated mapping over the real authoritative mapping template.")

    rows = build_rows()
    write_mapping(args.mapping_csv, rows)
    intake = validate_mapping_csv(args.mapping_csv).as_report()
    write_json(args.intake_report, intake)

    if not intake["ok"]:
        raise RuntimeError("Simulated mapping failed intake validation: " + "; ".join(intake["errors"]))

    report = {
        "schema_version": 1,
        "rhythm": "R05-A22",
        "ok": True,
        "decision": "SIMULATED_AUTHORITATIVE_DRIVE_MAPPING_INTAKE_PASS",
        "simulation_only": True,
        "authoritative_effect": "DENY",
        "download_allowed": False,
        "production_import_allowed": False,
        "retrieval_enablement_allowed": False,
        "mapping": {
            "path": str(args.mapping_csv),
            "sha256": sha256_file(args.mapping_csv),
            "row_count": len(rows),
            "simulated_drive_id_count": len({row["drive_file_id"] for row in rows}),
            "status": "AUTHORITATIVE_CONFIRMED_SHAPE_ONLY",
        },
        "intake_result": {
            "path": str(args.intake_report),
            "sha256": sha256_file(args.intake_report),
            "decision": intake["decision"],
            "ok": intake["ok"],
            "mode": intake["mode"],
            "record_count": intake["record_count"],
            "warnings": intake["warnings"],
        },
        "real_paths": {
            "real_mapping_path": str(REAL_MAPPING),
            "real_mapping_exists": REAL_MAPPING.exists(),
            "real_mapping_sha256": sha256_file(REAL_MAPPING) if REAL_MAPPING.exists() else None,
            "real_corrected_corpus_path": str(REAL_CORRECTED_CORPUS),
            "real_corrected_corpus_exists": REAL_CORRECTED_CORPUS.exists(),
        },
        "quality_controls": {
            "simulation_notice_column": True,
            "real_owner_approval_claim": False,
            "real_drive_id_claim": False,
            "real_binary_download": False,
            "raw_sha256_linkage": False,
            "parse_evidence": False,
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
            "Replace simulated Drive IDs with real owner-confirmed Drive file IDs, "
            "then request controlled one-file-per-execution download/hash/parse approval."
        ),
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }
    write_json(args.output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping-csv", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--intake-report", type=Path, default=DEFAULT_INTAKE_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "simulation_only": report["simulation_only"],
        "intake_decision": report["intake_result"]["decision"],
        "record_count": report["intake_result"]["record_count"],
        "real_corrected_corpus_exists": report["real_paths"]["real_corrected_corpus_exists"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
