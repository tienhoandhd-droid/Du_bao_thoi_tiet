#!/usr/bin/env python3
"""Apply QA Hoàn review input to the local A29 dashboard queue.

R05-A30 is intentionally local/source-only:

- record the accountable QA review for the 12 Drive reference documents;
- record that QA accepted the multi-engine OCR policy/method;
- keep the five OCR page-level decisions fail-closed until a reviewer gives
  explicit per-page decisions;
- do not enable AI use, production retrieval, Supabase, n8n, or Git remote work.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_QUEUE_JSON = ROOT / "work/r05_a29_review_dashboard_queue.json"
DEFAULT_REVIEWED_QUEUE_CSV = ROOT / "work/r05_a30_qa_hoan_reviewed_dashboard_queue.csv"
DEFAULT_REVIEWED_QUEUE_JSON = ROOT / "work/r05_a30_qa_hoan_reviewed_dashboard_queue.json"
DEFAULT_REPORT_JSON = ROOT / "work/r05_a30_qa_hoan_review_acceptance_report.json"
DEFAULT_REVIEW_INPUT_MD = ROOT / "work/r05_a30_qa_hoan_review_input.md"

GATE = "R05_A30_QA_HOAN_REVIEW_ACCEPTANCE"
SCHEMA_VERSION = 1
EXPECTED_DOCUMENT_COUNT = 12
EXPECTED_OCR_PAGE_COUNT = 5
EXPECTED_OCR_PAGES = ("1", "2", "3", "9", "17")

DOCUMENT_QUEUE_TYPE = "DOCUMENT_REFERENCE_REVIEW"
OCR_QUEUE_TYPE = "OCR_PAGE_REVIEW"
DOCUMENT_REVIEW_STATUS = "ACCOUNTABLE_HUMAN_REVIEWED"
OCR_POLICY_APPROVED_STATUS = "OCR_POLICY_APPROVED_PAGE_DECISION_PENDING"
DOCUMENT_REVIEW_DECISION = "ĐẠT"
OCR_PAGE_PENDING_DECISION = "CHƯA REVIEW"

REVIEWER = {
    "name": "Hoàn",
    "role": "QA",
    "reviewed_at": "2026-06-30T18:40:00+07:00",
    "reviewed_at_display": "30/06/2026 18:40",
}

REMOTE_OPERATIONS_NONE = {
    "supabase": [],
    "n8n": [],
    "git": [],
    "drive": [],
}

QUEUE_FIELDNAMES = [
    "queue_id",
    "queue_type",
    "dashboard_lane",
    "dashboard_column",
    "review_priority",
    "document_code",
    "document_title",
    "file_name",
    "drive_file_id",
    "drive_web_view_link",
    "source_sha256",
    "page_number",
    "sample_pages",
    "source_evidence_path",
    "multi_engine_policy_status",
    "technical_evidence_status",
    "extraction_path",
    "ocr_decision",
    "accurate_pair_agreement_pass",
    "accurate_passes_meet_mean_confidence",
    "all_pairwise_agreements_pass",
    "policy_required_machine_action",
    "policy_required_dashboard_action",
    "human_review_required",
    "reviewer_name",
    "reviewer_role",
    "review_status",
    "reviewed_at",
    "reviewer_decision",
    "reviewer_notes",
    "auto_approve",
    "ai_use_allowed",
    "production_retrieval",
    "remote_mutation_allowed",
]

DOCUMENT_REVIEW_NOTES = {
    "BS EN ISO 10993-16-2017.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, and final "
        "clarification states all 12 documents are accepted; source line still "
        "contained old choice placeholders, so A30 records the final 'Đạt cả' "
        "statement as controlling for document review only."
    ),
    "Cleanroom Management - Review.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2 readable."
    ),
    "ISO 8573-3.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,10,19 readable."
    ),
    "ISO 8573-7.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,7,14 readable."
    ),
    "ISO 8573-8.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,7,14 readable."
    ),
    "ISPE Automatic MACO Calculation (2021).pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,10,19 readable."
    ),
    "PDA TR 33.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,8,16 readable."
    ),
    "PDA TR 34.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,16,32 readable."
    ),
    "PDA TR 39 (2).pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,9,17 readable."
    ),
    "PDA TR 40.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,23,45 readable."
    ),
    "PDA TR 70.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,38,75 readable."
    ),
    "TR69_TOC.pdf": (
        "Tài liệu tham khảo. QA opened Drive, title/topic matched, sample pages 1,2,3,4,8 readable."
    ),
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in QUEUE_FIELDNAMES})


def true_cell(value: Any) -> bool:
    return str(value).strip().upper() == "TRUE"


def false_cell(value: Any) -> bool:
    return str(value).strip().upper() == "FALSE"


def base_fail_closed_pack(errors: list[str], source_queue_json_path: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE,
        "decision": "FAIL_CLOSED_INPUT_INVALID",
        "reviewer": REVIEWER,
        "source": {
            "source_queue_json": display_path(source_queue_json_path),
            "source_queue_sha256": "",
        },
        "summary": {
            "queue_item_count": 0,
            "document_review_items": 0,
            "document_accepted_count": 0,
            "ocr_page_review_items": 0,
            "ocr_policy_approved_by_qa": False,
            "ocr_page_decision_count": 0,
            "ocr_page_pending_count": 0,
            "blk004_status_after_review": "OPEN_FAIL_CLOSED_INVALID_INPUT",
            "blocked_p0_after_review": ["BLK-003", "BLK-004", "BLK-005", "BLK-006", "BLK-007"],
        },
        "input_anomalies": [],
        "remote_operations": deepcopy(REMOTE_OPERATIONS_NONE),
        "queue_items": [],
        "errors": errors,
    }


def validate_source_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    queue_items = payload.get("queue_items")
    if not isinstance(queue_items, list):
        return ["Source A29 queue JSON must contain a list field named queue_items."]

    document_items = [item for item in queue_items if item.get("queue_type") == DOCUMENT_QUEUE_TYPE]
    ocr_items = [item for item in queue_items if item.get("queue_type") == OCR_QUEUE_TYPE]

    if len(document_items) != EXPECTED_DOCUMENT_COUNT:
        errors.append(
            f"Expected {EXPECTED_DOCUMENT_COUNT} document review items; found {len(document_items)}."
        )
    if len(ocr_items) != EXPECTED_OCR_PAGE_COUNT:
        errors.append(f"Expected {EXPECTED_OCR_PAGE_COUNT} OCR page review items; found {len(ocr_items)}.")

    ocr_pages = sorted(item.get("page_number", "") for item in ocr_items)
    if ocr_pages != sorted(EXPECTED_OCR_PAGES):
        errors.append(f"Expected OCR pages {list(EXPECTED_OCR_PAGES)}; found {ocr_pages}.")

    document_names = {item.get("file_name", "") for item in document_items}
    missing_document_notes = sorted(set(DOCUMENT_REVIEW_NOTES) - document_names)
    extra_document_names = sorted(document_names - set(DOCUMENT_REVIEW_NOTES))
    if missing_document_notes or extra_document_names:
        errors.append(
            "Document queue does not match the QA review note set: "
            f"missing={missing_document_notes}, extra={extra_document_names}."
        )

    for item in queue_items:
        queue_id = item.get("queue_id", "<missing queue_id>")
        if item.get("human_review_required") != "TRUE":
            errors.append(f"{queue_id} must preserve human_review_required=TRUE.")
        if not false_cell(item.get("auto_approve")):
            errors.append(f"{queue_id} must preserve auto_approve=FALSE.")
        if not false_cell(item.get("ai_use_allowed")):
            errors.append(f"{queue_id} must preserve ai_use_allowed=FALSE.")
        if not false_cell(item.get("remote_mutation_allowed")):
            errors.append(f"{queue_id} must preserve remote_mutation_allowed=FALSE.")
        if item.get("production_retrieval") != "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS":
            errors.append(f"{queue_id} must keep production retrieval denied.")

    return errors


def apply_review(source_queue_json_path: Path = DEFAULT_SOURCE_QUEUE_JSON) -> dict[str, Any]:
    if not source_queue_json_path.is_file():
        return base_fail_closed_pack(
            [f"Source queue JSON not found: {display_path(source_queue_json_path)}"],
            source_queue_json_path,
        )

    payload = read_json(source_queue_json_path)
    errors = validate_source_payload(payload)
    if errors:
        pack = base_fail_closed_pack(errors, source_queue_json_path)
        pack["source"]["source_queue_sha256"] = sha256_file(source_queue_json_path)
        return pack

    reviewed_items: list[dict[str, Any]] = []
    input_anomalies = [
        {
            "severity": "warning",
            "scope": "DOCUMENT_REFERENCE_REVIEW",
            "message": (
                "The first document line still contained old decision/sample-page placeholders, "
                "but the reviewer later clarified 'Đạt cả'. A30 applies that final statement "
                "to document reference review only."
            ),
        },
        {
            "severity": "info",
            "scope": "OCR_PAGE_REVIEW",
            "message": (
                "Reviewer approved the multi-engine policy/method, but the page-level OCR "
                "template fields were left blank. A30 does not infer ĐẠT for any OCR page."
            ),
        },
    ]

    for source_item in payload["queue_items"]:
        item = deepcopy(source_item)
        item["reviewer_name"] = REVIEWER["name"]
        item["reviewer_role"] = REVIEWER["role"]
        item["reviewed_at"] = REVIEWER["reviewed_at"]

        if item.get("queue_type") == DOCUMENT_QUEUE_TYPE:
            item["review_status"] = DOCUMENT_REVIEW_STATUS
            item["reviewer_decision"] = DOCUMENT_REVIEW_DECISION
            item["reviewer_notes"] = DOCUMENT_REVIEW_NOTES.get(
                item.get("file_name", ""),
                "Tài liệu tham khảo. QA final statement records this document as accepted.",
            )
        elif item.get("queue_type") == OCR_QUEUE_TYPE:
            machine_status = item.get("multi_engine_policy_status", "")
            machine_action = item.get("policy_required_machine_action", "")
            dashboard_action = item.get("policy_required_dashboard_action", "")
            item["review_status"] = OCR_POLICY_APPROVED_STATUS
            item["reviewer_decision"] = OCR_PAGE_PENDING_DECISION
            item["reviewer_notes"] = (
                "QA approved the multi-engine OCR policy/method. Explicit per-page OCR "
                "decision was not supplied, so this page remains fail-closed. "
                f"Machine status={machine_status}; machine_action={machine_action}; "
                f"dashboard_action={dashboard_action}."
            )
        reviewed_items.append(item)

    document_items = [item for item in reviewed_items if item.get("queue_type") == DOCUMENT_QUEUE_TYPE]
    ocr_items = [item for item in reviewed_items if item.get("queue_type") == OCR_QUEUE_TYPE]
    ocr_pending_items = [
        item
        for item in ocr_items
        if item.get("reviewer_decision") == OCR_PAGE_PENDING_DECISION
        and item.get("review_status") == OCR_POLICY_APPROVED_STATUS
    ]
    page_status_counts = Counter(item.get("multi_engine_policy_status", "") for item in ocr_items)
    review_status_counts = Counter(item.get("review_status", "") for item in reviewed_items)

    summary = {
        "queue_item_count": len(reviewed_items),
        "document_review_items": len(document_items),
        "document_accepted_count": sum(
            1 for item in document_items if item.get("reviewer_decision") == DOCUMENT_REVIEW_DECISION
        ),
        "ocr_page_review_items": len(ocr_items),
        "ocr_policy_approved_by_qa": True,
        "ocr_page_decision_count": 0,
        "ocr_page_pending_count": len(ocr_pending_items),
        "ocr_policy_status_counts": dict(sorted(page_status_counts.items())),
        "review_status_counts": dict(sorted(review_status_counts.items())),
        "all_human_review_required": all(true_cell(item.get("human_review_required")) for item in reviewed_items),
        "all_auto_approve_false": all(false_cell(item.get("auto_approve")) for item in reviewed_items),
        "all_ai_use_allowed_false": all(false_cell(item.get("ai_use_allowed")) for item in reviewed_items),
        "all_remote_mutation_false": all(false_cell(item.get("remote_mutation_allowed")) for item in reviewed_items),
        "production_retrieval": "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS",
        "blk004_status_after_review": "OPEN_PARTIAL_PROGRESS_DOCUMENTS_REVIEWED_OCR_PAGES_PENDING",
        "blocked_p0_after_review": ["BLK-003", "BLK-004", "BLK-005", "BLK-006", "BLK-007"],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE,
        "decision": "LOCAL_PARTIAL_REVIEW_ACCEPTED_DOCUMENTS_ONLY_OCR_POLICY_APPROVED",
        "reviewer": REVIEWER,
        "source": {
            "source_queue_json": display_path(source_queue_json_path),
            "source_queue_sha256": sha256_file(source_queue_json_path),
            "drive_links_source": (
                "drive_web_view_link values copied from the A28/A29 local Drive catalog evidence; "
                "A30 performs no live Drive query, upload, sharing change, or remote mutation."
            ),
        },
        "summary": summary,
        "input_anomalies": input_anomalies,
        "remote_operations": deepcopy(REMOTE_OPERATIONS_NONE),
        "queue_items": reviewed_items,
        "errors": [],
    }


def build_review_input_markdown(pack: dict[str, Any]) -> str:
    reviewer = pack["reviewer"]
    document_items = [
        item for item in pack["queue_items"] if item.get("queue_type") == DOCUMENT_QUEUE_TYPE
    ]
    ocr_items = [item for item in pack["queue_items"] if item.get("queue_type") == OCR_QUEUE_TYPE]

    lines = [
        "# R05-A30 — QA Hoàn review input normalized",
        "",
        f"- Người review: `{reviewer['name']}`",
        f"- Vai trò: `{reviewer['role']}`",
        f"- Ngày/giờ review: `{reviewer['reviewed_at_display']}`",
        "- Scope: local-only acceptance recording; no live/remote mutation.",
        "",
        "## Normalization decision",
        "",
        "- 12 tài liệu Drive reference: recorded as `ĐẠT` because the reviewer stated `Đạt cả`.",
        "- Drive links are copied from local A28/A29 `drive_web_view_link` evidence; A30 did not call Drive live.",
        "- OCR for `PDA TR 39 (2).pdf`: reviewer approved the multi-engine policy/method, but did not give explicit page-level decisions. Therefore all five OCR pages remain `CHƯA REVIEW`.",
        "- `auto_approve=FALSE`, `ai_use_allowed=FALSE`, `remote_mutation_allowed=FALSE`, and production retrieval remains denied.",
        "",
        "## 12 tài liệu recorded as ĐẠT",
        "",
        "| # | File | Decision | Note |",
        "|---:|---|---|---|",
    ]
    for idx, item in enumerate(document_items, start=1):
        note = str(item.get("reviewer_notes", "")).replace("|", "\\|")
        lines.append(f"| {idx} | `{item.get('file_name', '')}` | `{item.get('reviewer_decision', '')}` | {note} |")

    lines.extend(
        [
            "",
            "## OCR policy approval recorded, page decisions pending",
            "",
            "| Page | Reviewer decision | Machine status | Required action kept |",
            "|---:|---|---|---|",
        ]
    )
    for item in sorted(ocr_items, key=lambda row: int(str(row.get("page_number", "0") or "0"))):
        lines.append(
            "| "
            f"{item.get('page_number', '')} | "
            f"`{item.get('reviewer_decision', '')}` | "
            f"`{item.get('multi_engine_policy_status', '')}` | "
            f"`{item.get('policy_required_machine_action', '')}` / "
            f"`{item.get('policy_required_dashboard_action', '')}` |"
        )

    lines.extend(
        [
            "",
            "## Input anomalies / guardrails",
            "",
        ]
    )
    for anomaly in pack.get("input_anomalies", []):
        lines.append(f"- `{anomaly['severity']}` / `{anomaly['scope']}`: {anomaly['message']}")

    return "\n".join(lines) + "\n"


def write_outputs(
    pack: dict[str, Any],
    queue_csv_path: Path = DEFAULT_REVIEWED_QUEUE_CSV,
    queue_json_path: Path = DEFAULT_REVIEWED_QUEUE_JSON,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    review_input_md_path: Path = DEFAULT_REVIEW_INPUT_MD,
) -> dict[str, Any]:
    if pack.get("errors"):
        raise ValueError("Refusing to write A30 outputs while pack has errors: " + "; ".join(pack["errors"]))

    queue_payload = {
        "schema_version": pack["schema_version"],
        "gate": pack["gate"],
        "decision": pack["decision"],
        "reviewer": pack["reviewer"],
        "source": pack["source"],
        "summary": pack["summary"],
        "input_anomalies": pack["input_anomalies"],
        "remote_operations": pack["remote_operations"],
        "queue_items": pack["queue_items"],
    }
    report_payload = {
        key: value for key, value in queue_payload.items() if key != "queue_items"
    }
    report_payload["outputs"] = {
        "queue_csv": display_path(queue_csv_path),
        "queue_json": display_path(queue_json_path),
        "report_json": display_path(report_json_path),
        "review_input_md": display_path(review_input_md_path),
    }

    write_csv(queue_csv_path, pack["queue_items"])
    write_json(queue_json_path, queue_payload)
    write_json(report_json_path, report_payload)
    review_input_md_path.parent.mkdir(parents=True, exist_ok=True)
    review_input_md_path.write_text(build_review_input_markdown(pack), encoding="utf-8")
    return report_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-queue-json", type=Path, default=DEFAULT_SOURCE_QUEUE_JSON)
    parser.add_argument("--queue-csv", type=Path, default=DEFAULT_REVIEWED_QUEUE_CSV)
    parser.add_argument("--queue-json", type=Path, default=DEFAULT_REVIEWED_QUEUE_JSON)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--review-input-md", type=Path, default=DEFAULT_REVIEW_INPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pack = apply_review(args.source_queue_json)
    if pack.get("errors"):
        print(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    report = write_outputs(
        pack,
        queue_csv_path=args.queue_csv,
        queue_json_path=args.queue_json,
        report_json_path=args.report_json,
        review_input_md_path=args.review_input_md,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
