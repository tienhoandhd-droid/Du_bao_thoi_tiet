#!/usr/bin/env python3
"""Validate a 12-file light-PDF sample set before any controlled n8n probe.

This gate is intentionally not an authoritative corpus gate. It only proves that
the sample set is safe enough to ask for a bounded download/hash/parse probe.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_HEADERS = (
    "Tên tài liệu",
    "ID",
    "Trạng thái",
    "file_name",
    "Kiểu file",
    "size_bytes",
    "parent_path",
)
SAMPLE_STATUS = "UNVERIFIED_RANDOM_LIGHT_SAMPLE"
AUTHORITATIVE_STATUS_MARKERS = ("AUTHORITATIVE", "CONFIRMED", "APPROVED")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def inventory_by_id(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    return {row["id"]: row for row in read_rows(path)}


def validate_sample_set(
    sample_csv: Path,
    inventory_csv: Path | None = None,
    max_bytes: int = 1024 * 1024,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not sample_csv.exists():
        return {
            "ok": False,
            "decision": "FAIL_CLOSED",
            "errors": [f"Sample CSV not found: {sample_csv}"],
            "warnings": [],
            "records": [],
        }

    rows = read_rows(sample_csv)
    inv = inventory_by_id(inventory_csv)

    if rows:
        missing_headers = [header for header in REQUIRED_HEADERS if header not in rows[0]]
        if missing_headers:
            errors.append("Missing required headers: " + ", ".join(missing_headers) + ".")

    if len(rows) != 12:
        errors.append(f"Expected exactly 12 sample rows; found {len(rows)}.")

    seen_ids: set[str] = set()
    records: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=2):
        title = (row.get("Tên tài liệu") or "").strip()
        drive_id = (row.get("ID") or "").strip()
        status = (row.get("Trạng thái") or "").strip()
        file_name = (row.get("file_name") or "").strip()
        mime_type = (row.get("Kiểu file") or "").strip()
        parent_path = (row.get("parent_path") or "").strip()

        try:
            size_bytes = int((row.get("size_bytes") or "").strip())
        except ValueError:
            size_bytes = -1

        record = {
            "row": idx,
            "title": title,
            "drive_file_id": drive_id,
            "status": status,
            "file_name": file_name,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "parent_path": parent_path,
        }
        records.append(record)

        if not drive_id:
            errors.append(f"Row {idx}: missing Drive file ID.")
        elif drive_id in seen_ids:
            errors.append(f"Row {idx}: duplicate Drive file ID {drive_id}.")
        seen_ids.add(drive_id)

        if status != SAMPLE_STATUS:
            errors.append(f"Row {idx}: status must be {SAMPLE_STATUS}, got {status!r}.")
        if any(marker in status.upper() for marker in AUTHORITATIVE_STATUS_MARKERS):
            errors.append(f"Row {idx}: sample status must not claim authoritative approval.")
        if mime_type != "application/pdf":
            errors.append(f"Row {idx}: MIME type must be application/pdf, got {mime_type!r}.")
        if not file_name.lower().endswith(".pdf"):
            errors.append(f"Row {idx}: file_name must end with .pdf.")
        if size_bytes <= 0:
            errors.append(f"Row {idx}: size_bytes must be positive.")
        elif size_bytes > max_bytes:
            errors.append(f"Row {idx}: size_bytes {size_bytes} exceeds max {max_bytes}.")
        if title and file_name and title != file_name:
            errors.append(f"Row {idx}: Tên tài liệu and file_name differ.")

        if inv:
            inventory_record = inv.get(drive_id)
            if inventory_record is None:
                errors.append(f"Row {idx}: Drive ID not found in metadata inventory.")
            else:
                checks = {
                    "name": file_name,
                    "mime_type": mime_type,
                    "size_bytes": str(size_bytes),
                    "parent_path": parent_path,
                }
                for inventory_field, expected_value in checks.items():
                    actual_value = (inventory_record.get(inventory_field) or "").strip()
                    if actual_value != expected_value:
                        errors.append(
                            f"Row {idx}: inventory mismatch for {inventory_field}: "
                            f"{actual_value!r} != {expected_value!r}."
                        )

    if not errors:
        warnings.append(
            "This 12-PDF set is valid only as an unverified light sample. It must not "
            "close BLK-003/004 or feed citation runtime as authoritative corpus evidence."
        )

    ordered_records = sorted(records, key=lambda record: (record["size_bytes"], record["file_name"]))
    return {
        "ok": not errors,
        "decision": "READY_FOR_APPROVAL" if not errors else "FAIL_CLOSED",
        "mode": "light_pdf_sample_probe_gate",
        "sample_csv": str(sample_csv),
        "inventory_csv": str(inventory_csv) if inventory_csv else None,
        "row_count": len(rows),
        "max_bytes": max_bytes,
        "total_size_bytes": sum(record["size_bytes"] for record in records if record["size_bytes"] > 0),
        "records": ordered_records,
        "execution_controls": {
            "scope": "controlled TKTL sample probe only",
            "one_file_per_execution": True,
            "concurrency": 1,
            "download_binary": "after exact user approval only",
            "parse_mode": "bounded metadata/hash/page-count/text-layer probe; OCR/table full pass excluded",
            "supabase_writes": "DENY",
            "n8n_publish_archive_update": "DENY",
            "corpus_import_indexing": "DENY",
            "authoritative_closure_claim": "DENY",
        },
        "remote_operations": {
            "supabase": [],
            "n8n": [],
            "git": [],
        },
        "errors": errors,
        "warnings": warnings,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-csv", type=Path, required=True)
    parser.add_argument("--inventory-csv", type=Path)
    parser.add_argument("--max-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = validate_sample_set(args.sample_csv, args.inventory_csv, args.max_bytes)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
