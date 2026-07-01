#!/usr/bin/env python3
"""Build the local R05-A18 authoritative-input readiness report.

The operator fingerprints the current mapping/corpus inputs, runs the strict R05
intake and P0 prerequisite gates, and preserves the R05-A17 rejected-candidate
boundary. It performs no network request or remote mutation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from r05_a13_p0_closure_gate import build_report as build_p0_gate_report
from r05_authoritative_corpus_intake import (
    AUTHORITATIVE_STATUS,
    ID_COLUMNS,
    STATUS_COLUMNS,
    first_present,
    is_placeholder,
    sha256_file,
    validate_corpus_dir,
    validate_mapping_csv,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "work/r05_authoritative_12_file_mapping.csv"
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_A17_REPORT = ROOT / "work/r05_a17_drive_authoritative_multimodal_accession_report.json"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def mapping_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "sha256": None,
            "size_bytes": 0,
            "row_count": 0,
            "authoritative_confirmed_count": 0,
            "concrete_drive_id_count": 0,
            "status_counts": {},
        }

    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    statuses = [first_present(row, STATUS_COLUMNS) for row in rows]
    drive_ids = [first_present(row, ID_COLUMNS) for row in rows]
    return {
        "path": str(path),
        "exists": True,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "row_count": len(rows),
        "authoritative_confirmed_count": sum(
            status.upper() == AUTHORITATIVE_STATUS for status in statuses
        ),
        "concrete_drive_id_count": sum(not is_placeholder(file_id) for file_id in drive_ids),
        "status_counts": dict(sorted(Counter(status or "<EMPTY>" for status in statuses).items())),
    }


def corpus_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "inventory_sha256": None,
            "file_count": 0,
            "total_bytes": 0,
            "files": [],
        }

    files = sorted(item for item in path.rglob("*") if item.is_file() and not item.name.startswith("."))
    entries = [
        {
            "relative_path": str(item.relative_to(path)),
            "size_bytes": item.stat().st_size,
            "sha256": sha256_file(item),
        }
        for item in files
    ]
    return {
        "path": str(path),
        "exists": True,
        "inventory_sha256": stable_json_sha256(entries),
        "file_count": len(entries),
        "total_bytes": sum(entry["size_bytes"] for entry in entries),
        "files": entries,
    }


def intake_summary(result: Any) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "decision": "PASS" if result.ok else "FAIL_CLOSED",
        "mode": result.mode,
        "record_count": len(result.records),
        "errors": result.errors,
        "warnings": result.warnings,
    }


def prior_accession_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "sha256": None,
            "quality_boundary_preserved": False,
            "errors": ["R05-A17 accession report is missing."],
        }

    report = json.loads(path.read_text(encoding="utf-8"))
    summary = report.get("summary") or {}
    selected = {
        "eligible_exact_pdf_candidates_total": summary.get("eligible_exact_pdf_candidates_total"),
        "binary_downloads_performed": summary.get("binary_downloads_performed"),
        "authoritative_confirmed_records": summary.get("authoritative_confirmed_records"),
        "decision": summary.get("decision"),
    }
    quality_boundary_preserved = (
        selected["eligible_exact_pdf_candidates_total"] == 0
        and selected["binary_downloads_performed"] == 0
        and selected["authoritative_confirmed_records"] == 0
    )
    return {
        "path": str(path),
        "exists": True,
        "sha256": sha256_file(path),
        "quality_boundary_preserved": quality_boundary_preserved,
        "summary": selected,
        "errors": [] if quality_boundary_preserved else [
            "R05-A17 report no longer proves the rejected-candidate boundary."
        ],
    }


def previous_fingerprint(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = report.get("input_fingerprint")
    return value if isinstance(value, str) and value else None


def build_report(
    mapping_csv: Path,
    corpus_dir: Path,
    a17_report: Path,
    previous_report: Path | None = None,
) -> dict[str, Any]:
    mapping = mapping_evidence(mapping_csv)
    corpus = corpus_evidence(corpus_dir)
    mapping_intake = validate_mapping_csv(mapping_csv)
    corpus_intake = validate_corpus_dir(corpus_dir)
    prerequisite_gate = build_p0_gate_report(mapping_csv, corpus_dir)
    accession = prior_accession_evidence(a17_report)

    fingerprint_payload = {
        "mapping_sha256": mapping["sha256"],
        "corpus_inventory_sha256": corpus["inventory_sha256"],
    }
    fingerprint = stable_json_sha256(fingerprint_payload)
    prior_fingerprint = previous_fingerprint(previous_report)
    valid_input_modes = [
        mode
        for mode, result in (("mapping_csv", mapping_intake), ("corpus_dir", corpus_intake))
        if result.ok
    ]
    ok = bool(valid_input_modes) and accession["quality_boundary_preserved"]
    decision = (
        "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN"
        if ok
        else "FAIL_CLOSED_INPUT_REQUIRED"
    )

    return {
        "schema_version": 1,
        "rhythm": "R05-A18",
        "gate": "P0_AUTHORITATIVE_INPUT_READINESS",
        "ok": ok,
        "decision": decision,
        "input_fingerprint": fingerprint,
        "freshness": {
            "previous_report_path": str(previous_report) if previous_report else None,
            "previous_fingerprint": prior_fingerprint,
            "baseline_available": prior_fingerprint is not None,
            "changed_since_previous": None if prior_fingerprint is None else prior_fingerprint != fingerprint,
        },
        "inputs": {
            "mapping_csv": {**mapping, "intake": intake_summary(mapping_intake)},
            "corpus_dir": {**corpus, "intake": intake_summary(corpus_intake)},
        },
        "valid_input_modes": valid_input_modes,
        "prerequisite_gate": {
            "ok": prerequisite_gate["ok"],
            "decision": prerequisite_gate["decision"],
            "input_checks": prerequisite_gate["input_checks"],
        },
        "prior_accession": accession,
        "quality_controls": {
            "required_mapping_status": AUTHORITATIVE_STATUS,
            "required_mime_type": "application/pdf",
            "local_pdf_signature_required": True,
            "duplicate_drive_ids_denied": True,
            "duplicate_binary_sha256_denied": True,
            "rejected_a17_candidates_promoted": 0,
            "random_light_sample_eligible_for_closure": False,
            "auto_authoritative_approval": False,
        },
        "blockers": {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "next_step": (
            "Prepare an exact, separately approved controlled one-file-per-execution hash/parse plan."
            if ok
            else "Supply 12 exact human-confirmed Drive PDF mappings or the corrected 12-PDF local corpus, then rerun R05-A18."
        ),
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping-csv", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--a17-report", type=Path, default=DEFAULT_A17_REPORT)
    parser.add_argument("--previous-report", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    prior_report = args.previous_report
    if prior_report is None and args.output and args.output.exists():
        prior_report = args.output

    report = build_report(args.mapping_csv, args.corpus_dir, args.a17_report, prior_report)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
