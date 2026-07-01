#!/usr/bin/env python3
"""Build và kiểm tra catalog Drive-native cho R05-A28.

Operator này chỉ đọc evidence local và tạo artifact local. Quyết định của người
dùng là chọn một catalog tài liệu tham khảo riêng; quyết định đó không được hiểu
là phê duyệt nội dung GMP hoặc cho phép ghi Supabase/n8n/Git remote.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "work/r05_a03_drive_metadata_inventory.csv"
DEFAULT_REVIEW_QUEUE = ROOT / "work/r05_a26_blk004_corpus_review_queue.csv"
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_CATALOG_OUTPUT = ROOT / "work/r05_a28_drive_native_catalog.csv"
DEFAULT_RETIRE_OUTPUT = ROOT / "work/r05_a28_internal_sop_retirement_plan.csv"
DEFAULT_REPORT_OUTPUT = ROOT / "work/r05_a28_drive_native_catalog_report.json"

CATALOG_SPECS = (
    ("REF-ISO-10993-16-2017", "BS EN ISO 10993-16-2017.pdf", "BS EN ISO 10993-16:2017", "ISO/BSI"),
    ("REF-CLEANROOM-MGMT-REVIEW", "Cleanroom Management - Review.pdf", "Cleanroom Management - Review", "External reference"),
    ("REF-ISO-8573-3", "ISO 8573-3.pdf", "ISO 8573-3", "ISO"),
    ("REF-ISO-8573-7", "ISO 8573-7.pdf", "ISO 8573-7", "ISO"),
    ("REF-ISO-8573-8", "ISO 8573-8.pdf", "ISO 8573-8", "ISO"),
    ("REF-ISPE-MACO-2021", "ISPE Automatic MACO Calculation (2021).pdf", "ISPE Automatic MACO Calculation (2021)", "ISPE"),
    ("REF-PDA-TR-033", "PDA TR 33.pdf", "PDA Technical Report 33", "PDA"),
    ("REF-PDA-TR-034", "PDA TR 34.pdf", "PDA Technical Report 34", "PDA"),
    ("REF-PDA-TR-039", "PDA TR 39 (2).pdf", "PDA Technical Report 39", "PDA"),
    ("REF-PDA-TR-040", "PDA TR 40.pdf", "PDA Technical Report 40", "PDA"),
    ("REF-PDA-TR-070", "PDA TR 70.pdf", "PDA Technical Report 70", "PDA"),
    ("REF-PDA-TR-069-TOC", "TR69_TOC.pdf", "PDA Technical Report 69 - Table of Contents", "PDA"),
)

LEGACY_INTERNAL_SOPS = tuple(f"GMP-SOP-{index:03d}" for index in range(1, 11))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report(
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    review_queue_path: Path = DEFAULT_REVIEW_QUEUE,
    corpus_dir: Path = DEFAULT_CORPUS,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for path in (inventory_path, review_queue_path):
        if not path.exists():
            errors.append(f"Thiếu input: {path}")
    if not corpus_dir.is_dir():
        errors.append(f"Thiếu corpus local: {corpus_dir}")
    if errors:
        return {
            "gate": "R05_A28_DRIVE_NATIVE_CATALOG",
            "decision": "FAIL_CLOSED_MISSING_INPUT",
            "errors": errors,
            "warnings": warnings,
            "catalog_records": [],
            "retirement_plan": [],
        }

    inventory = read_csv(inventory_path)
    review_rows = read_csv(review_queue_path)
    inventory_by_name: dict[str, list[dict[str, str]]] = {}
    for row in inventory:
        inventory_by_name.setdefault(row.get("name", ""), []).append(row)
    review_by_name = {row.get("file_name", ""): row for row in review_rows}

    records: list[dict[str, Any]] = []
    used_drive_ids: set[str] = set()
    used_hashes: set[str] = set()
    for document_code, file_name, title, organization in CATALOG_SPECS:
        inventory_matches = [
            row
            for row in inventory_by_name.get(file_name, [])
            if row.get("mime_type") == "application/pdf"
        ]
        if len(inventory_matches) != 1:
            errors.append(
                f"{file_name}: cần đúng một PDF trong inventory Drive; tìm thấy {len(inventory_matches)}."
            )
            continue
        inventory_row = inventory_matches[0]
        review_row = review_by_name.get(file_name)
        if not review_row:
            errors.append(f"{file_name}: thiếu hàng đợi review A26.")
            continue
        local_path = corpus_dir / file_name
        if not local_path.is_file():
            errors.append(f"{file_name}: thiếu binary local để đối chiếu SHA-256.")
            continue

        local_sha = sha256_file(local_path)
        evidence_sha = review_row.get("source_sha256", "").lower()
        if local_sha != evidence_sha:
            errors.append(f"{file_name}: SHA-256 local không khớp evidence A26.")
        drive_id = inventory_row.get("id", "")
        if not drive_id or drive_id in used_drive_ids:
            errors.append(f"{file_name}: Drive file ID thiếu hoặc trùng.")
        if local_sha in used_hashes:
            errors.append(f"{file_name}: binary SHA-256 trùng một catalog record khác.")
        used_drive_ids.add(drive_id)
        used_hashes.add(local_sha)

        records.append(
            {
                "document_code": document_code,
                "document_title": title,
                "original_file_name": file_name,
                "drive_file_id": drive_id,
                "drive_parent_path": inventory_row.get("parent_path", ""),
                "drive_web_view_link": inventory_row.get("web_view_link", ""),
                "mime_type": inventory_row.get("mime_type", ""),
                "size_bytes": int(inventory_row.get("size_bytes") or local_path.stat().st_size),
                "binary_sha256": local_sha,
                "document_type": "guideline",
                "source_type": "guideline",
                "source_category": "external_reference",
                "source_organization": organization,
                "catalog_action": "CREATE_DRIVE_NATIVE_REFERENCE_RECORD",
                "catalog_scope_decision": "USER_DIRECTED_SEPARATE_DRIVE_CATALOG",
                "content_review_status": "PENDING_ACCOUNTABLE_HUMAN_REVIEW",
                "technical_evidence_status": review_row.get("technical_evidence_status", ""),
                "extraction_path": review_row.get("extraction_path", ""),
                "approved_for_ai_use": False,
                "dashboard_lane": "REFERENCE_LIBRARY_REVIEW_LANE",
                "production_retrieval": "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS",
            }
        )

    expected_names = {spec[1] for spec in CATALOG_SPECS}
    unexpected_review_names = sorted(set(review_by_name) - expected_names)
    missing_review_names = sorted(expected_names - set(review_by_name))
    if unexpected_review_names:
        errors.append("Review queue có file ngoài catalog A28: " + ", ".join(unexpected_review_names))
    if missing_review_names:
        errors.append("Review queue thiếu file catalog A28: " + ", ".join(missing_review_names))
    if len(records) != 12:
        errors.append(f"Catalog phải có đúng 12 record; hiện dựng được {len(records)}.")
    if any(record["document_code"].startswith("GMP-SOP-") for record in records):
        errors.append("Catalog Drive không được tái sử dụng mã của SOP nội bộ placeholder.")
    if any(record["approved_for_ai_use"] for record in records):
        errors.append("Quyết định phạm vi catalog không được tự động phê duyệt nội dung cho AI.")

    retirement_plan = [
        {
            "document_code": code,
            "requested_scope": "TEN_INTERNAL_SOP_PLACEHOLDERS_ONLY",
            "transition_action": "RETIRE_FROM_ACTIVE_DASHBOARD_PRESERVE_LINEAGE",
            "target_document_status": "archived",
            "target_approved_for_ai_use": False,
            "current_version_action": "PRESERVE_IMMUTABLE_EVIDENCE",
            "chunk_action": "PRESERVE_AND_KEEP_NON_SEARCHABLE",
            "document_access_action": "PREFLIGHT_THEN_DEACTIVATE_IF_PRESENT",
            "hard_delete": False,
            "remote_execution_status": "NOT_AUTHORIZED_NOT_EXECUTED",
        }
        for code in LEGACY_INTERNAL_SOPS
    ]

    warnings.append(
        "VQ-QT-003 và WHO-TRS-996 không nằm trong phạm vi retire 10 SOP; tiếp tục fail-closed cho tới quyết định riêng."
    )
    warnings.append(
        "Catalog scope đã được người dùng chọn nhưng review nội dung, AI approval và remote mutation vẫn chưa được cấp."
    )

    decision = (
        "LOCAL_READY_REMOTE_APPROVAL_AND_HUMAN_REVIEW_REQUIRED"
        if not errors
        else "FAIL_CLOSED_CATALOG_EVIDENCE_MISMATCH"
    )
    return {
        "gate": "R05_A28_DRIVE_NATIVE_CATALOG",
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "catalog_record_count": len(records),
        "retirement_record_count": len(retirement_plan),
        "catalog_records": records,
        "retirement_plan": retirement_plan,
        "blockers": {
            "BLK-003": "LOCAL_SCOPE_RESOLVED_REMOTE_CATALOG_VERSION_LINEAGE_REQUIRED",
            "BLK-004": "OPEN_ACCOUNTABLE_HUMAN_REVIEW_REQUIRED",
            "BLK-005": "OPEN_POST_INGEST_CHUNK_EMBEDDING_RECERTIFICATION_REQUIRED",
            "BLK-006": "OPEN_DEPLOYED_CHUNK_VERSION_FK_AND_RUNTIME_CITATION_REQUIRED",
            "BLK-007": "OPEN_DOWNSTREAM_U10_U15_REQUIRED",
        },
        "controls": {
            "source_binary_renamed": False,
            "legacy_rows_hard_deleted": False,
            "human_content_approval_inferred": False,
            "supabase_write": False,
            "n8n_mutation_or_execution": False,
            "git_remote": False,
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--catalog-output", type=Path, default=DEFAULT_CATALOG_OUTPUT)
    parser.add_argument("--retire-output", type=Path, default=DEFAULT_RETIRE_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    args = parser.parse_args()

    report = build_report(
        inventory_path=args.inventory,
        review_queue_path=args.review_queue,
        corpus_dir=args.corpus,
    )
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if report.get("catalog_records"):
        write_csv(args.catalog_output, report["catalog_records"])
    if report.get("retirement_plan"):
        write_csv(args.retire_output, report["retirement_plan"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["decision"] == "LOCAL_READY_REMOTE_APPROVAL_AND_HUMAN_REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
