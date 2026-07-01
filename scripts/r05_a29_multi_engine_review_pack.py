#!/usr/bin/env python3
"""Build review pack/dashboard queue cho R05-A29.

Operator này chỉ tạo artefact local từ evidence A26/A28. Nó mã hoá policy
multi-engine do người dùng nêu:

- nhiều engine/scan giống nhau thì chỉ được xem là technical pass candidate;
- engine khác nhau thì phải retry một lần;
- retry vẫn khác nhau hoặc confidence thấp thì đưa lên dashboard để phê duyệt;
- không tự động phê duyệt nội dung, không bật AI/retrieval, không đụng remote.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "work/r05_a28_drive_native_catalog.csv"
DEFAULT_DOCUMENT_REVIEW_QUEUE = ROOT / "work/r05_a26_blk004_corpus_review_queue.csv"
DEFAULT_OCR_REVIEW_QUEUE = ROOT / "work/r05_a26_ocr_page_review_queue.csv"
DEFAULT_QUEUE_CSV = ROOT / "work/r05_a29_review_dashboard_queue.csv"
DEFAULT_QUEUE_JSON = ROOT / "work/r05_a29_review_dashboard_queue.json"
DEFAULT_POLICY_JSON = ROOT / "work/r05_a29_multi_engine_policy.json"
DEFAULT_REVIEW_TEMPLATE = ROOT / "work/r05_a29_reviewer_input_template.md"
DEFAULT_REPORT_JSON = ROOT / "work/r05_a29_multi_engine_review_pack_report.json"

EXPECTED_DOCUMENT_COUNT = 12
EXPECTED_OCR_PAGE_COUNT = 5
EXPECTED_OCR_PAGES = ("1", "2", "3", "9", "17")
PDA_TR39_FILE = "PDA TR 39 (2).pdf"

GATE = "R05_A29_MULTI_ENGINE_REVIEW_PACK"
QUEUE_SCHEMA_VERSION = 1
HUMAN_REVIEW_STATUS = "PENDING_ACCOUNTABLE_HUMAN_REVIEW"
PENDING_DECISION = "PENDING"
FALSE_CELL = "FALSE"
TRUE_CELL = "TRUE"

POLICY: dict[str, Any] = {
    "schema_version": QUEUE_SCHEMA_VERSION,
    "gate": GATE,
    "policy_name": "CRAVE_BLK004_MULTI_ENGINE_REVIEW_POLICY",
    "user_policy_summary": (
        "Nếu các engine/quét hình ảnh cho kết quả giống nhau thì technical pass "
        "candidate; nếu khác nhau thì tự quét lại thêm một lần; nếu vẫn khác "
        "hoặc confidence thấp thì đưa lên dashboard để người có trách nhiệm phê duyệt."
    ),
    "allowed_human_decisions": ["ĐẠT", "KHÔNG ĐẠT", "CHƯA REVIEW"],
    "rules": [
        {
            "rule_id": "ME-01",
            "condition": "engines_match_and_confidence_ok",
            "machine_action": "NO_RETRY_REQUIRED",
            "queue_status": "MULTI_ENGINE_MATCH_PASS_PENDING_HUMAN_REVIEW",
            "dashboard_action": "HUMAN_REVIEW_REQUIRED_BEFORE_ACCEPTANCE",
        },
        {
            "rule_id": "ME-02",
            "condition": "engine_outputs_disagree",
            "machine_action": "RETRY_ONCE_WITH_INDEPENDENT_ENGINE_SET",
            "queue_status": "ENGINE_DISAGREEMENT_RETRY_REQUIRED",
            "dashboard_action": "ESCALATE_IF_RETRY_STILL_DIFFERS",
        },
        {
            "rule_id": "ME-03",
            "condition": "retry_still_disagrees",
            "machine_action": "STOP_AUTOMATION_AND_KEEP_FAIL_CLOSED",
            "queue_status": "PERSISTENT_DISAGREEMENT_DASHBOARD_APPROVAL_REQUIRED",
            "dashboard_action": "ACCOUNTABLE_HUMAN_APPROVAL_REQUIRED",
        },
        {
            "rule_id": "ME-04",
            "condition": "confidence_below_threshold_or_insufficient_text",
            "machine_action": "RETRY_OR_EXCLUDE_UNLESS_HUMAN_APPROVED",
            "queue_status": "LOW_CONFIDENCE_DASHBOARD_APPROVAL_REQUIRED",
            "dashboard_action": "ACCOUNTABLE_HUMAN_APPROVAL_REQUIRED",
        },
    ],
    "fail_closed_controls": {
        "auto_approve": False,
        "ai_use_allowed": False,
        "production_retrieval": "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS",
        "supabase_write": False,
        "n8n_mutation_or_execution": False,
        "git_remote": False,
    },
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in QUEUE_FIELDNAMES})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def bool_cell(value: str) -> bool:
    return value.strip().upper() == TRUE_CELL


def false_cell(value: str) -> bool:
    return value.strip().upper() == FALSE_CELL


def classify_document_policy_status(extraction_path: str) -> str:
    if "OCR" in extraction_path.upper():
        return "OCR_PAGE_QUEUE_ATTACHED_PENDING_HUMAN_REVIEW"
    return "TEXT_LAYER_TECHNICAL_EVIDENCE_PENDING_HUMAN_REVIEW"


def classify_ocr_policy(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    """Return status, machine_action, dashboard_action, column, priority."""
    confidence_ok = bool_cell(row.get("accurate_passes_meet_mean_confidence", ""))
    all_pairwise_ok = bool_cell(row.get("all_pairwise_agreements_pass", ""))
    accurate_pair_ok = bool_cell(row.get("accurate_pair_agreement_pass", ""))
    decision = row.get("ocr_decision", "")

    if all_pairwise_ok and confidence_ok:
        return (
            "MULTI_ENGINE_MATCH_PASS_PENDING_HUMAN_REVIEW",
            "NO_RETRY_REQUIRED",
            "HUMAN_REVIEW_REQUIRED_BEFORE_ACCEPTANCE",
            "Tài liệu tham khảo / Chờ review",
            "P0_BLK004_OCR_HUMAN_REVIEW",
        )
    if "LOW_CONFIDENCE" in decision or not confidence_ok:
        return (
            "LOW_CONFIDENCE_DASHBOARD_APPROVAL_REQUIRED",
            "RETRY_OR_EXCLUDE_UNLESS_HUMAN_APPROVED",
            "ACCOUNTABLE_HUMAN_APPROVAL_REQUIRED",
            "OCR low confidence / Cần phê duyệt",
            "P0_BLK004_OCR_ESCALATION",
        )
    if accurate_pair_ok and not all_pairwise_ok:
        return (
            "ENGINE_DISAGREEMENT_RETRY_REQUIRED",
            "RETRY_ONCE_WITH_INDEPENDENT_ENGINE_SET",
            "ESCALATE_IF_RETRY_STILL_DIFFERS",
            "OCR variance / Cần retry hoặc phê duyệt",
            "P0_BLK004_OCR_ESCALATION",
        )
    return (
        "OCR_REVIEW_REQUIRED_FAIL_CLOSED",
        "STOP_AUTOMATION_AND_KEEP_FAIL_CLOSED",
        "ACCOUNTABLE_HUMAN_APPROVAL_REQUIRED",
        "OCR review / Cần xử lý",
        "P0_BLK004_OCR_ESCALATION",
    )


def validate_inputs(
    catalog_rows: list[dict[str, str]],
    document_rows: list[dict[str, str]],
    ocr_rows: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []

    if len(catalog_rows) != EXPECTED_DOCUMENT_COUNT:
        errors.append(f"Catalog A28 phải có {EXPECTED_DOCUMENT_COUNT} dòng; hiện có {len(catalog_rows)}.")
    if len(document_rows) != EXPECTED_DOCUMENT_COUNT:
        errors.append(
            f"Document review queue A26 phải có {EXPECTED_DOCUMENT_COUNT} dòng; hiện có {len(document_rows)}."
        )
    if len(ocr_rows) != EXPECTED_OCR_PAGE_COUNT:
        errors.append(
            f"OCR review queue A26 phải có {EXPECTED_OCR_PAGE_COUNT} dòng; hiện có {len(ocr_rows)}."
        )

    catalog_by_file = {row.get("original_file_name", ""): row for row in catalog_rows}
    document_by_file = {row.get("file_name", ""): row for row in document_rows}
    if len(catalog_by_file) != len(catalog_rows):
        errors.append("Catalog A28 có original_file_name bị trùng.")
    if len(document_by_file) != len(document_rows):
        errors.append("Document review queue A26 có file_name bị trùng.")

    catalog_names = set(catalog_by_file)
    document_names = set(document_by_file)
    if catalog_names != document_names:
        errors.append(
            "Catalog A28 và document review queue A26 không cùng tập file: "
            f"missing_in_review={sorted(catalog_names - document_names)}, "
            f"extra_in_review={sorted(document_names - catalog_names)}."
        )

    for file_name, catalog_row in catalog_by_file.items():
        review_row = document_by_file.get(file_name)
        if not review_row:
            continue
        catalog_sha = catalog_row.get("binary_sha256", "").lower()
        review_sha = review_row.get("source_sha256", "").lower()
        if catalog_sha != review_sha:
            errors.append(f"{file_name}: SHA-256 catalog A28 không khớp review queue A26.")
        if catalog_row.get("content_review_status") != HUMAN_REVIEW_STATUS:
            errors.append(f"{file_name}: catalog content_review_status không pending human review.")
        if review_row.get("review_status") != HUMAN_REVIEW_STATUS:
            errors.append(f"{file_name}: review_status không pending human review.")
        if review_row.get("reviewer_decision") != PENDING_DECISION:
            errors.append(f"{file_name}: reviewer_decision không phải PENDING.")
        if not false_cell(review_row.get("auto_approve", "")):
            errors.append(f"{file_name}: auto_approve phải là FALSE.")
        if bool_cell(catalog_row.get("approved_for_ai_use", "")):
            errors.append(f"{file_name}: approved_for_ai_use phải fail-closed/False.")

    ocr_pages = tuple(row.get("page_number", "") for row in ocr_rows)
    if ocr_pages != EXPECTED_OCR_PAGES:
        errors.append(f"OCR pages phải là {EXPECTED_OCR_PAGES}; hiện là {ocr_pages}.")
    pda_sha = catalog_by_file.get(PDA_TR39_FILE, {}).get("binary_sha256", "").lower()
    for row in ocr_rows:
        page = row.get("page_number", "")
        if row.get("file_name") != PDA_TR39_FILE:
            errors.append(f"OCR page {page}: file_name phải là {PDA_TR39_FILE}.")
        if pda_sha and row.get("source_sha256", "").lower() != pda_sha:
            errors.append(f"OCR page {page}: source_sha256 không khớp catalog PDA TR 39.")
        if row.get("review_status") != HUMAN_REVIEW_STATUS:
            errors.append(f"OCR page {page}: review_status không pending human review.")
        if row.get("reviewer_decision") != PENDING_DECISION:
            errors.append(f"OCR page {page}: reviewer_decision không phải PENDING.")
        if not false_cell(row.get("auto_approve", "")):
            errors.append(f"OCR page {page}: auto_approve phải là FALSE.")

    return errors


def build_document_queue_item(
    *,
    index: int,
    catalog_row: dict[str, str],
    document_row: dict[str, str],
    document_review_queue_path: Path,
) -> dict[str, str]:
    extraction_path = document_row.get("extraction_path", "")
    document_code = catalog_row.get("document_code", "")
    policy_status = classify_document_policy_status(extraction_path)
    machine_action = (
        "SEE_ATTACHED_OCR_PAGE_QUEUE"
        if "OCR" in extraction_path.upper()
        else "NO_ADDITIONAL_MACHINE_SCAN_REQUIRED_FOR_TEXT_LAYER"
    )
    return {
        "queue_id": f"R05-A29-DOC-{index:02d}-{document_code}",
        "queue_type": "DOCUMENT_REFERENCE_REVIEW",
        "dashboard_lane": catalog_row.get("dashboard_lane", "REFERENCE_LIBRARY_REVIEW_LANE"),
        "dashboard_column": "Tài liệu tham khảo / Chờ review",
        "review_priority": "P0_BLK004_DOCUMENT_REVIEW",
        "document_code": document_code,
        "document_title": catalog_row.get("document_title", ""),
        "file_name": document_row.get("file_name", ""),
        "drive_file_id": catalog_row.get("drive_file_id", ""),
        "drive_web_view_link": catalog_row.get("drive_web_view_link", ""),
        "source_sha256": document_row.get("source_sha256", ""),
        "page_number": "",
        "sample_pages": document_row.get("sample_pages", ""),
        "source_evidence_path": display_path(document_review_queue_path),
        "multi_engine_policy_status": policy_status,
        "technical_evidence_status": document_row.get("technical_evidence_status", ""),
        "extraction_path": extraction_path,
        "ocr_decision": "",
        "accurate_pair_agreement_pass": "",
        "accurate_passes_meet_mean_confidence": "",
        "all_pairwise_agreements_pass": "",
        "policy_required_machine_action": machine_action,
        "policy_required_dashboard_action": "HUMAN_DOCUMENT_REVIEW_REQUIRED_BEFORE_ACCEPTANCE",
        "human_review_required": TRUE_CELL,
        "reviewer_name": document_row.get("reviewer_name", ""),
        "reviewer_role": document_row.get("reviewer_role", ""),
        "review_status": document_row.get("review_status", HUMAN_REVIEW_STATUS),
        "reviewed_at": document_row.get("reviewed_at", ""),
        "reviewer_decision": document_row.get("reviewer_decision", PENDING_DECISION),
        "reviewer_notes": document_row.get("reviewer_notes", ""),
        "auto_approve": FALSE_CELL,
        "ai_use_allowed": FALSE_CELL,
        "production_retrieval": catalog_row.get(
            "production_retrieval",
            "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS",
        ),
        "remote_mutation_allowed": FALSE_CELL,
    }


def build_ocr_queue_item(
    *,
    index: int,
    catalog_row: dict[str, str],
    ocr_row: dict[str, str],
    ocr_review_queue_path: Path,
) -> dict[str, str]:
    status, machine_action, dashboard_action, dashboard_column, priority = classify_ocr_policy(ocr_row)
    page = ocr_row.get("page_number", "")
    document_code = catalog_row.get("document_code", "")
    return {
        "queue_id": f"R05-A29-OCR-{index:02d}-{document_code}-P{int(page):03d}",
        "queue_type": "OCR_PAGE_REVIEW",
        "dashboard_lane": catalog_row.get("dashboard_lane", "REFERENCE_LIBRARY_REVIEW_LANE"),
        "dashboard_column": dashboard_column,
        "review_priority": priority,
        "document_code": document_code,
        "document_title": catalog_row.get("document_title", ""),
        "file_name": ocr_row.get("file_name", ""),
        "drive_file_id": catalog_row.get("drive_file_id", ""),
        "drive_web_view_link": catalog_row.get("drive_web_view_link", ""),
        "source_sha256": ocr_row.get("source_sha256", ""),
        "page_number": page,
        "sample_pages": page,
        "source_evidence_path": display_path(ocr_review_queue_path),
        "multi_engine_policy_status": status,
        "technical_evidence_status": "BOUNDED_OCR_TECHNICAL_EVIDENCE_RECORDED",
        "extraction_path": "BOUNDED_MULTI_PASS_VISION_OCR",
        "ocr_decision": ocr_row.get("ocr_decision", ""),
        "accurate_pair_agreement_pass": ocr_row.get("accurate_pair_agreement_pass", ""),
        "accurate_passes_meet_mean_confidence": ocr_row.get("accurate_passes_meet_mean_confidence", ""),
        "all_pairwise_agreements_pass": ocr_row.get("all_pairwise_agreements_pass", ""),
        "policy_required_machine_action": machine_action,
        "policy_required_dashboard_action": dashboard_action,
        "human_review_required": TRUE_CELL,
        "reviewer_name": ocr_row.get("reviewer_name", ""),
        "reviewer_role": ocr_row.get("reviewer_role", ""),
        "review_status": ocr_row.get("review_status", HUMAN_REVIEW_STATUS),
        "reviewed_at": ocr_row.get("reviewed_at", ""),
        "reviewer_decision": ocr_row.get("reviewer_decision", PENDING_DECISION),
        "reviewer_notes": ocr_row.get("reviewer_notes", ""),
        "auto_approve": FALSE_CELL,
        "ai_use_allowed": FALSE_CELL,
        "production_retrieval": catalog_row.get(
            "production_retrieval",
            "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS",
        ),
        "remote_mutation_allowed": FALSE_CELL,
    }


def build_review_template(queue_items: list[dict[str, str]]) -> str:
    document_items = [row for row in queue_items if row["queue_type"] == "DOCUMENT_REFERENCE_REVIEW"]
    ocr_items = [row for row in queue_items if row["queue_type"] == "OCR_PAGE_REVIEW"]
    lines: list[str] = [
        "# R05-A29 Reviewer Input Template",
        "",
        "Người review:",
        "Vai trò:",
        "Ngày/giờ review:",
        "",
        "## Cách review 12 tài liệu",
        "",
        "- Chọn `ĐẠT` chỉ khi bạn đã mở đúng file/Drive link, đối chiếu tên tài liệu, SHA/source identity, phạm vi dùng làm tài liệu tham khảo, sample pages và ghi chú đủ rủi ro.",
        "- Chọn `KHÔNG ĐẠT` nếu sai tài liệu, không đọc được, không phù hợp dashboard lane, có nghi vấn bản quyền/phạm vi, hoặc evidence kỹ thuật không đủ để người chịu trách nhiệm chấp nhận.",
        "- Chọn `CHƯA REVIEW` nếu chưa tự xem trực tiếp. Không để Codex/AI tự ký thay.",
        "- Dù technical evidence pass, `approved_for_ai_use` vẫn giữ `FALSE` cho tới khi có quyết định người chịu trách nhiệm và các gate embed/citation sau đó.",
        "",
        "## Cách review OCR PDA TR 39",
        "",
        "- So sánh kết quả từ tối thiểu 2 engine/quét ảnh độc lập với hình trang gốc.",
        "- Nếu các engine giống nhau và confidence đạt: có thể đánh dấu technical pass candidate, nhưng vẫn cần người review chọn `ĐẠT/KHÔNG ĐẠT/CHƯA REVIEW`.",
        "- Nếu engine khác nhau: chạy lại một lần bằng bộ engine/quét độc lập. Nếu vẫn khác, giữ fail-closed và đưa lên dashboard phê duyệt.",
        "- Nếu low-confidence: không dùng tự động; cần retry/exclude hoặc người chịu trách nhiệm phê duyệt rõ ràng.",
        "",
        "## Review 12 tài liệu",
        "",
    ]
    for idx, item in enumerate(document_items, start=1):
        lines.extend(
            [
                f"{idx}. {item['file_name']}: ĐẠT / KHÔNG ĐẠT / CHƯA REVIEW",
                f"   Queue ID: {item['queue_id']}",
                f"   Document code: {item['document_code']}",
                f"   Drive link: {item['drive_web_view_link']}",
                f"   SHA-256: {item['source_sha256']}",
                f"   Sample pages: {item['sample_pages']}",
                "   Ghi chú:",
            ]
        )
    lines.extend(["", "## Review OCR cho PDA TR 39 (2).pdf", ""])
    for item in ocr_items:
        lines.extend(
            [
                f"- Trang {item['page_number']}: ĐẠT / KHÔNG ĐẠT / CHƯA REVIEW",
                f"  Queue ID: {item['queue_id']}",
                f"  Policy status: {item['multi_engine_policy_status']}",
                f"  Machine action: {item['policy_required_machine_action']}",
                f"  Dashboard action: {item['policy_required_dashboard_action']}",
                "  Ghi chú:",
            ]
        )
    lines.extend(
        [
            "",
            "## Ghi chú chung",
            "",
            "- Không có dòng nào được auto-approve.",
            "- Không có dòng nào được phép AI/retrieval production trước khi review, version/chunk/embed/citation gates PASS.",
            "- Nếu cần cập nhật dashboard live, phải lập exact change set và xin xác nhận riêng.",
            "",
        ]
    )
    return "\n".join(lines)


def build_pack(
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    document_review_queue_path: Path = DEFAULT_DOCUMENT_REVIEW_QUEUE,
    ocr_review_queue_path: Path = DEFAULT_OCR_REVIEW_QUEUE,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for path in (catalog_path, document_review_queue_path, ocr_review_queue_path):
        if not path.exists():
            errors.append(f"Thiếu input: {path}")
    if errors:
        return {
            "schema_version": QUEUE_SCHEMA_VERSION,
            "gate": GATE,
            "decision": "FAIL_CLOSED_MISSING_INPUT",
            "errors": errors,
            "warnings": warnings,
            "policy": POLICY,
            "queue_items": [],
            "summary": {},
        }

    catalog_rows = read_csv(catalog_path)
    document_rows = read_csv(document_review_queue_path)
    ocr_rows = read_csv(ocr_review_queue_path)
    errors.extend(validate_inputs(catalog_rows, document_rows, ocr_rows))

    catalog_by_file = {row["original_file_name"]: row for row in catalog_rows}
    document_by_file = {row["file_name"]: row for row in document_rows}
    queue_items: list[dict[str, str]] = []
    for index, catalog_row in enumerate(catalog_rows, start=1):
        file_name = catalog_row.get("original_file_name", "")
        document_row = document_by_file.get(file_name)
        if not document_row:
            continue
        queue_items.append(
            build_document_queue_item(
                index=index,
                catalog_row=catalog_row,
                document_row=document_row,
                document_review_queue_path=document_review_queue_path,
            )
        )

    pda_catalog_row = catalog_by_file.get(PDA_TR39_FILE, {})
    for index, ocr_row in enumerate(ocr_rows, start=1):
        queue_items.append(
            build_ocr_queue_item(
                index=index,
                catalog_row=pda_catalog_row,
                ocr_row=ocr_row,
                ocr_review_queue_path=ocr_review_queue_path,
            )
        )

    if len(queue_items) != EXPECTED_DOCUMENT_COUNT + EXPECTED_OCR_PAGE_COUNT:
        errors.append(
            "Dashboard queue phải có 17 items "
            f"(12 document + 5 OCR); hiện có {len(queue_items)}."
        )
    if any(item.get("auto_approve") != FALSE_CELL for item in queue_items):
        errors.append("Dashboard queue có dòng không fail-closed auto_approve=FALSE.")
    if any(item.get("ai_use_allowed") != FALSE_CELL for item in queue_items):
        errors.append("Dashboard queue có dòng bật AI use trái policy.")
    if any(item.get("remote_mutation_allowed") != FALSE_CELL for item in queue_items):
        errors.append("Dashboard queue có dòng cho phép remote mutation trái scope.")

    type_counts = Counter(item["queue_type"] for item in queue_items)
    policy_counts = Counter(item["multi_engine_policy_status"] for item in queue_items)
    ocr_policy_counts = Counter(
        item["multi_engine_policy_status"]
        for item in queue_items
        if item["queue_type"] == "OCR_PAGE_REVIEW"
    )
    summary = {
        "queue_item_count": len(queue_items),
        "document_review_items": type_counts.get("DOCUMENT_REFERENCE_REVIEW", 0),
        "ocr_page_review_items": type_counts.get("OCR_PAGE_REVIEW", 0),
        "dashboard_lanes": sorted({item["dashboard_lane"] for item in queue_items}),
        "queue_type_counts": dict(sorted(type_counts.items())),
        "policy_status_counts": dict(sorted(policy_counts.items())),
        "ocr_policy_status_counts": dict(sorted(ocr_policy_counts.items())),
        "all_human_review_required": all(item["human_review_required"] == TRUE_CELL for item in queue_items),
        "all_auto_approve_false": all(item["auto_approve"] == FALSE_CELL for item in queue_items),
        "all_ai_use_allowed_false": all(item["ai_use_allowed"] == FALSE_CELL for item in queue_items),
        "all_remote_mutation_false": all(item["remote_mutation_allowed"] == FALSE_CELL for item in queue_items),
        "blocked_p0_after_pack": ["BLK-003", "BLK-004", "BLK-005", "BLK-006", "BLK-007"],
    }
    warnings.append(
        "R05-A29 tạo dashboard queue local-only; chưa ghi Supabase/n8n/dashboard live và chưa đóng BLK-004."
    )
    warnings.append(
        "Các dòng ĐẠT/KHÔNG ĐẠT/CHƯA REVIEW phải do người chịu trách nhiệm nhập sau khi xem tài liệu/trang gốc."
    )

    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "gate": GATE,
        "decision": "LOCAL_READY_REVIEW_DASHBOARD_QUEUE_CREATED"
        if not errors
        else "FAIL_CLOSED_INPUT_INVALID",
        "errors": errors,
        "warnings": warnings,
        "policy": POLICY,
        "summary": summary,
        "queue_items": queue_items,
        "remote_operations": {
            "supabase": [],
            "n8n": [],
            "git": [],
        },
    }


def write_outputs(
    pack: dict[str, Any],
    *,
    queue_csv_path: Path = DEFAULT_QUEUE_CSV,
    queue_json_path: Path = DEFAULT_QUEUE_JSON,
    policy_json_path: Path = DEFAULT_POLICY_JSON,
    review_template_path: Path = DEFAULT_REVIEW_TEMPLATE,
    report_json_path: Path = DEFAULT_REPORT_JSON,
) -> dict[str, Any]:
    queue_items = pack.get("queue_items", [])
    queue_payload = {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "gate": GATE,
        "decision": pack.get("decision"),
        "summary": pack.get("summary", {}),
        "queue_items": queue_items,
    }
    write_csv(queue_csv_path, queue_items)
    write_json(queue_json_path, queue_payload)
    write_json(policy_json_path, POLICY)
    review_template_path.parent.mkdir(parents=True, exist_ok=True)
    review_template_path.write_text(
        build_review_template(queue_items),
        encoding="utf-8",
    )

    output_files = {
        "queue_csv": display_path(queue_csv_path),
        "queue_json": display_path(queue_json_path),
        "policy_json": display_path(policy_json_path),
        "review_template": display_path(review_template_path),
    }
    output_hashes = {
        key: sha256_file(path)
        for key, path in {
            "queue_csv": queue_csv_path,
            "queue_json": queue_json_path,
            "policy_json": policy_json_path,
            "review_template": review_template_path,
        }.items()
    }
    report_payload = {
        key: value
        for key, value in pack.items()
        if key not in {"queue_items", "policy"}
    }
    report_payload["output_files"] = output_files
    report_payload["output_sha256"] = output_hashes
    report_payload["policy_file"] = output_files["policy_json"]
    report_payload["queue_file"] = output_files["queue_json"]
    report_payload["queue_csv_file"] = output_files["queue_csv"]
    report_payload["review_template_file"] = output_files["review_template"]
    write_json(report_json_path, report_payload)
    return report_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--document-review-queue", type=Path, default=DEFAULT_DOCUMENT_REVIEW_QUEUE)
    parser.add_argument("--ocr-review-queue", type=Path, default=DEFAULT_OCR_REVIEW_QUEUE)
    parser.add_argument("--queue-csv-output", type=Path, default=DEFAULT_QUEUE_CSV)
    parser.add_argument("--queue-json-output", type=Path, default=DEFAULT_QUEUE_JSON)
    parser.add_argument("--policy-json-output", type=Path, default=DEFAULT_POLICY_JSON)
    parser.add_argument("--review-template-output", type=Path, default=DEFAULT_REVIEW_TEMPLATE)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_JSON)
    args = parser.parse_args()

    pack = build_pack(
        catalog_path=args.catalog,
        document_review_queue_path=args.document_review_queue,
        ocr_review_queue_path=args.ocr_review_queue,
    )
    if pack["decision"] == "LOCAL_READY_REVIEW_DASHBOARD_QUEUE_CREATED":
        console_payload = write_outputs(
            pack,
            queue_csv_path=args.queue_csv_output,
            queue_json_path=args.queue_json_output,
            policy_json_path=args.policy_json_output,
            review_template_path=args.review_template_output,
            report_json_path=args.report_output,
        )
    else:
        console_payload = {key: value for key, value in pack.items() if key != "queue_items"}
        write_json(args.report_output, console_payload)
    print(json.dumps(console_payload, ensure_ascii=False, indent=2))
    return 0 if pack["decision"] == "LOCAL_READY_REVIEW_DASHBOARD_QUEUE_CREATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
