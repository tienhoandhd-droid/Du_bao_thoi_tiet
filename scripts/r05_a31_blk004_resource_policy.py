#!/usr/bin/env python3
"""Close BLK-004 under the resource-aware multi-engine policy accepted by user.

R05-A31 does not change live systems. It records a practical closure policy:

- nhiều công cụ/quét khác nhau cho kết quả giống nhau => pass for BLK-004;
- nếu khác nhau, thử retry/nâng chất lượng/chọn engine route tốt hơn;
- nếu vẫn khác hoặc confidence thấp, tạo note cho AL kiểm bản gốc và chọn mục đúng nhất;
- do nguồn lực hiện tại hạn chế, persistent variance/low-confidence pages become
  AL backlog items instead of blocking BLK-004 forever;
- this closes BLK-004 as index-readiness evidence only, not as a 100% OCR truth claim.
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
DEFAULT_A30_QUEUE_JSON = ROOT / "work/r05_a30_qa_hoan_reviewed_dashboard_queue.json"
DEFAULT_POLICY_JSON = ROOT / "work/r05_a31_blk004_resource_policy.json"
DEFAULT_CLOSURE_QUEUE_JSON = ROOT / "work/r05_a31_blk004_resource_closure_queue.json"
DEFAULT_CLOSURE_QUEUE_CSV = ROOT / "work/r05_a31_blk004_resource_closure_queue.csv"
DEFAULT_AL_BACKLOG_CSV = ROOT / "work/r05_a31_blk004_al_escalation_backlog.csv"
DEFAULT_REPORT_JSON = ROOT / "work/r05_a31_blk004_resource_policy_closure_report.json"

GATE = "R05_A31_BLK004_RESOURCE_AWARE_POLICY_CLOSURE"
SCHEMA_VERSION = 1
SOURCE_QUEUE_TYPE_DOC = "DOCUMENT_REFERENCE_REVIEW"
SOURCE_QUEUE_TYPE_OCR = "OCR_PAGE_REVIEW"
EXPECTED_DOCUMENT_COUNT = 12
EXPECTED_OCR_PAGES = {"1", "2", "3", "9", "17"}
FALSE_CELL = "FALSE"
TRUE_CELL = "TRUE"

POLICY_ACCEPTED_AT = "2026-06-30T19:20:00+07:00"
POLICY_APPROVER = {
    "name": "Project owner instruction in chat",
    "role": "Owner/AL escalation policy approver",
    "accepted_at": POLICY_ACCEPTED_AT,
}

PRODUCTION_RETRIEVAL_DENY = "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS"

RESOURCE_POLICY: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "gate": GATE,
    "policy_name": "BLK004_RESOURCE_AWARE_MULTI_ENGINE_POLICY",
    "accepted_at": POLICY_ACCEPTED_AT,
    "accepted_by": POLICY_APPROVER,
    "user_policy_summary": [
        "Nhiều công cụ quét khác nhau cho kết quả giống nhau thì pass.",
        "Nếu kết quả khác nhau thì thay đổi cách quét hoặc nâng cao chất lượng; nếu kết quả sau đó giống nhau thì pass.",
        "Nếu vẫn khác nhau hoặc confidence thấp thì đưa note cho AL check với bản gốc; mục nào AL xác định đúng nhất sẽ pass.",
        "Do nguồn lực hiện tại hạn chế, persistent variance/low-confidence pages được đưa vào backlog AL/nâng cấp sau thay vì chặn BLK-004 mãi.",
        "Không tuyên bố đạt 100%; đây là closure theo risk acceptance và operational guardrail.",
    ],
    "acceptance_rules": [
        {
            "rule_id": "BLK004-ME-01",
            "condition": "all_pairwise_agreements_pass=true and confidence_ok=true",
            "blk004_disposition": "PASS_MULTI_ENGINE_MATCH",
            "al_note_required": False,
        },
        {
            "rule_id": "BLK004-ME-02",
            "condition": "engine_variance but accurate_pair_agreement_pass=true and confidence_ok=true",
            "blk004_disposition": "PASS_WITH_VARIANCE_AL_NOTE",
            "al_note_required": True,
        },
        {
            "rule_id": "BLK004-ME-03",
            "condition": "low_confidence or persistent disagreement",
            "blk004_disposition": "PASS_WITH_LOW_CONFIDENCE_AL_NOTE",
            "al_note_required": True,
        },
    ],
    "guardrails": {
        "no_100_percent_claim": True,
        "future_upgrade_required": True,
        "ai_use_allowed": False,
        "auto_approve": False,
        "production_retrieval": PRODUCTION_RETRIEVAL_DENY,
        "supabase_write": False,
        "n8n_mutation_or_execution": False,
        "git_remote": False,
        "drive_live_mutation": False,
    },
}

QUEUE_FIELDNAMES = [
    "queue_id",
    "queue_type",
    "file_name",
    "document_code",
    "page_number",
    "source_review_status",
    "source_reviewer_decision",
    "source_multi_engine_policy_status",
    "source_ocr_decision",
    "accurate_pair_agreement_pass",
    "accurate_passes_meet_mean_confidence",
    "all_pairwise_agreements_pass",
    "blk004_disposition",
    "blk004_closure_accepted",
    "al_note_required",
    "future_upgrade_required",
    "production_ai_use_allowed",
    "production_retrieval",
    "closure_note",
]

AL_BACKLOG_FIELDNAMES = [
    "backlog_id",
    "queue_id",
    "file_name",
    "page_number",
    "reason",
    "machine_status",
    "required_al_action",
    "source_page_reference",
    "status",
]


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


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def bool_cell(value: Any) -> bool:
    return str(value or "").strip().upper() == TRUE_CELL


def false_cell(value: Any) -> bool:
    return str(value or "").strip().upper() == FALSE_CELL


def fail_closed(errors: list[str], source_path: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE,
        "decision": "FAIL_CLOSED_INPUT_INVALID",
        "policy": RESOURCE_POLICY,
        "source": {
            "a30_queue_json": display_path(source_path),
            "a30_queue_sha256": sha256_file(source_path) if source_path.is_file() else "",
        },
        "summary": {
            "blk004_status_after_a31": "OPEN_FAIL_CLOSED_INVALID_INPUT",
            "document_items": 0,
            "document_pass_count": 0,
            "ocr_items": 0,
            "ocr_closed_for_blk004_count": 0,
            "al_backlog_count": 0,
            "open_p0_after_blk004_closure": ["BLK-003", "BLK-004", "BLK-005", "BLK-006", "BLK-007"],
        },
        "closure_items": [],
        "al_backlog": [],
        "remote_operations": {"drive": [], "git": [], "n8n": [], "supabase": []},
        "errors": errors,
    }


def validate_source(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    items = payload.get("queue_items")
    if not isinstance(items, list):
        return ["A30 queue JSON must contain list field queue_items."]

    docs = [item for item in items if item.get("queue_type") == SOURCE_QUEUE_TYPE_DOC]
    ocr = [item for item in items if item.get("queue_type") == SOURCE_QUEUE_TYPE_OCR]
    if len(docs) != EXPECTED_DOCUMENT_COUNT:
        errors.append(f"Expected {EXPECTED_DOCUMENT_COUNT} document items; found {len(docs)}.")
    ocr_pages = {str(item.get("page_number", "")) for item in ocr}
    if ocr_pages != EXPECTED_OCR_PAGES:
        errors.append(f"Expected OCR pages {sorted(EXPECTED_OCR_PAGES)}; found {sorted(ocr_pages)}.")

    for item in docs:
        queue_id = item.get("queue_id", "<missing queue_id>")
        if item.get("review_status") != "ACCOUNTABLE_HUMAN_REVIEWED":
            errors.append(f"{queue_id} must be ACCOUNTABLE_HUMAN_REVIEWED before A31 closure.")
        if item.get("reviewer_decision") != "ĐẠT":
            errors.append(f"{queue_id} must have reviewer_decision=ĐẠT before A31 closure.")

    for item in items:
        queue_id = item.get("queue_id", "<missing queue_id>")
        if not false_cell(item.get("auto_approve")):
            errors.append(f"{queue_id} must preserve auto_approve=FALSE.")
        if not false_cell(item.get("ai_use_allowed")):
            errors.append(f"{queue_id} must preserve ai_use_allowed=FALSE.")
        if item.get("production_retrieval") != PRODUCTION_RETRIEVAL_DENY:
            errors.append(f"{queue_id} must keep production retrieval denied.")
        if not false_cell(item.get("remote_mutation_allowed")):
            errors.append(f"{queue_id} must preserve remote_mutation_allowed=FALSE.")

    return errors


def classify_ocr_item(item: dict[str, Any]) -> tuple[str, bool, str]:
    all_match = bool_cell(item.get("all_pairwise_agreements_pass"))
    confidence_ok = bool_cell(item.get("accurate_passes_meet_mean_confidence"))
    accurate_pair_ok = bool_cell(item.get("accurate_pair_agreement_pass"))
    machine_status = str(item.get("multi_engine_policy_status", ""))

    if all_match and confidence_ok:
        return (
            "PASS_MULTI_ENGINE_MATCH",
            False,
            "Nhiều engine/quét giống nhau và confidence đạt; pass BLK-004 theo policy mới.",
        )
    if accurate_pair_ok and confidence_ok:
        return (
            "PASS_WITH_VARIANCE_AL_NOTE",
            True,
            (
                "Có variance giữa engine nhưng accurate-pair agreement và confidence đạt. "
                "Theo policy mới, không chặn BLK-004; giữ note cho AL nếu cần so bản gốc."
            ),
        )
    return (
        "PASS_WITH_LOW_CONFIDENCE_AL_NOTE",
        True,
        (
            f"Machine status {machine_status} còn low-confidence/persistent variance. "
            "Theo policy mới, đóng BLK-004 với AL note/backlog và nâng cấp sau."
        ),
    )


def build_closure(source_queue_json_path: Path = DEFAULT_A30_QUEUE_JSON) -> dict[str, Any]:
    if not source_queue_json_path.is_file():
        return fail_closed([f"Missing A30 queue JSON: {display_path(source_queue_json_path)}"], source_queue_json_path)

    payload = read_json(source_queue_json_path)
    errors = validate_source(payload)
    if errors:
        return fail_closed(errors, source_queue_json_path)

    closure_items: list[dict[str, Any]] = []
    al_backlog: list[dict[str, Any]] = []

    for source_item in payload["queue_items"]:
        queue_type = source_item.get("queue_type", "")
        if queue_type == SOURCE_QUEUE_TYPE_DOC:
            disposition = "PASS_QA_DOCUMENT_REVIEW_ACCEPTED"
            al_required = False
            note = "Document reference was accountable-human reviewed by QA and accepted as ĐẠT in A30."
        elif queue_type == SOURCE_QUEUE_TYPE_OCR:
            disposition, al_required, note = classify_ocr_item(source_item)
        else:
            disposition = "UNKNOWN_FAIL_CLOSED"
            al_required = True
            note = "Unexpected queue type; retained as AL backlog."

        closure_item = {
            "queue_id": source_item.get("queue_id", ""),
            "queue_type": queue_type,
            "file_name": source_item.get("file_name", ""),
            "document_code": source_item.get("document_code", ""),
            "page_number": source_item.get("page_number", ""),
            "source_review_status": source_item.get("review_status", ""),
            "source_reviewer_decision": source_item.get("reviewer_decision", ""),
            "source_multi_engine_policy_status": source_item.get("multi_engine_policy_status", ""),
            "source_ocr_decision": source_item.get("ocr_decision", ""),
            "accurate_pair_agreement_pass": source_item.get("accurate_pair_agreement_pass", ""),
            "accurate_passes_meet_mean_confidence": source_item.get("accurate_passes_meet_mean_confidence", ""),
            "all_pairwise_agreements_pass": source_item.get("all_pairwise_agreements_pass", ""),
            "blk004_disposition": disposition,
            "blk004_closure_accepted": TRUE_CELL,
            "al_note_required": TRUE_CELL if al_required else FALSE_CELL,
            "future_upgrade_required": TRUE_CELL if al_required else FALSE_CELL,
            "production_ai_use_allowed": FALSE_CELL,
            "production_retrieval": PRODUCTION_RETRIEVAL_DENY,
            "closure_note": note,
        }
        closure_items.append(closure_item)

        if al_required and queue_type == SOURCE_QUEUE_TYPE_OCR:
            backlog_id = f"R05-A31-AL-P{str(source_item.get('page_number', '')).zfill(3)}"
            al_backlog.append(
                {
                    "backlog_id": backlog_id,
                    "queue_id": source_item.get("queue_id", ""),
                    "file_name": source_item.get("file_name", ""),
                    "page_number": source_item.get("page_number", ""),
                    "reason": disposition,
                    "machine_status": source_item.get("multi_engine_policy_status", ""),
                    "required_al_action": (
                        "Khi có nguồn lực, AL mở bản gốc/crop trang này, đối chiếu OCR/table/figure "
                        "và chọn nội dung đúng nhất để promote."
                    ),
                    "source_page_reference": f"{source_item.get('file_name', '')} page {source_item.get('page_number', '')}",
                    "status": "BACKLOG_ACCEPTED_NOT_BLOCKING_BLK004",
                }
            )

    disposition_counts = Counter(item["blk004_disposition"] for item in closure_items)
    docs = [item for item in closure_items if item["queue_type"] == SOURCE_QUEUE_TYPE_DOC]
    ocr = [item for item in closure_items if item["queue_type"] == SOURCE_QUEUE_TYPE_OCR]

    summary = {
        "blk004_status_after_a31": "CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED",
        "document_items": len(docs),
        "document_pass_count": sum(1 for item in docs if item["blk004_closure_accepted"] == TRUE_CELL),
        "ocr_items": len(ocr),
        "ocr_closed_for_blk004_count": sum(1 for item in ocr if item["blk004_closure_accepted"] == TRUE_CELL),
        "ocr_multi_engine_match_pass_count": disposition_counts.get("PASS_MULTI_ENGINE_MATCH", 0),
        "ocr_variance_al_note_count": disposition_counts.get("PASS_WITH_VARIANCE_AL_NOTE", 0),
        "ocr_low_confidence_al_note_count": disposition_counts.get("PASS_WITH_LOW_CONFIDENCE_AL_NOTE", 0),
        "al_backlog_count": len(al_backlog),
        "future_upgrade_required": True,
        "no_100_percent_claim": True,
        "production_ai_use_allowed": False,
        "production_retrieval": PRODUCTION_RETRIEVAL_DENY,
        "open_p0_after_blk004_closure": ["BLK-003", "BLK-005", "BLK-006", "BLK-007"],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE,
        "decision": "BLK004_CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED_SOURCE_ONLY",
        "policy": RESOURCE_POLICY,
        "source": {
            "a30_queue_json": display_path(source_queue_json_path),
            "a30_queue_sha256": sha256_file(source_queue_json_path),
        },
        "summary": summary,
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "closure_items": closure_items,
        "al_backlog": al_backlog,
        "future_upgrade_ideas": [
            "Tạo dashboard AL side-by-side: source page crop, OCR text, table/figure crop, diff giữa các engine.",
            "Thêm confidence calibration: chỉ tự pass khi agreement và confidence vượt threshold đã đo bằng golden pages.",
            "Lưu provenance line/bbox cho OCR/table để AL click về đúng vùng trên bản gốc.",
            "Tách ingestion policy: uncertain snippets được exclude hoặc quarantine đến khi AL promote.",
            "Tạo active-learning backlog để ưu tiên review các trang có variance/low confidence trước.",
        ],
        "remote_operations": {"drive": [], "git": [], "n8n": [], "supabase": []},
        "errors": [],
    }


def write_outputs(
    closure: dict[str, Any],
    policy_json_path: Path = DEFAULT_POLICY_JSON,
    closure_queue_json_path: Path = DEFAULT_CLOSURE_QUEUE_JSON,
    closure_queue_csv_path: Path = DEFAULT_CLOSURE_QUEUE_CSV,
    al_backlog_csv_path: Path = DEFAULT_AL_BACKLOG_CSV,
    report_json_path: Path = DEFAULT_REPORT_JSON,
) -> dict[str, Any]:
    if closure.get("errors"):
        raise ValueError("Refusing to write A31 outputs while closure has errors: " + "; ".join(closure["errors"]))

    write_json(policy_json_path, closure["policy"])
    write_json(
        closure_queue_json_path,
        {
            "schema_version": closure["schema_version"],
            "gate": closure["gate"],
            "decision": closure["decision"],
            "summary": closure["summary"],
            "closure_items": closure["closure_items"],
            "al_backlog": closure["al_backlog"],
            "remote_operations": closure["remote_operations"],
        },
    )
    write_csv(closure_queue_csv_path, closure["closure_items"], QUEUE_FIELDNAMES)
    write_csv(al_backlog_csv_path, closure["al_backlog"], AL_BACKLOG_FIELDNAMES)

    report_payload = {
        key: value
        for key, value in closure.items()
        if key not in {"closure_items", "al_backlog"}
    }
    report_payload["outputs"] = {
        "policy_json": display_path(policy_json_path),
        "closure_queue_json": display_path(closure_queue_json_path),
        "closure_queue_csv": display_path(closure_queue_csv_path),
        "al_backlog_csv": display_path(al_backlog_csv_path),
        "report_json": display_path(report_json_path),
    }
    write_json(report_json_path, report_payload)
    return report_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a30-queue-json", type=Path, default=DEFAULT_A30_QUEUE_JSON)
    parser.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY_JSON)
    parser.add_argument("--closure-queue-json", type=Path, default=DEFAULT_CLOSURE_QUEUE_JSON)
    parser.add_argument("--closure-queue-csv", type=Path, default=DEFAULT_CLOSURE_QUEUE_CSV)
    parser.add_argument("--al-backlog-csv", type=Path, default=DEFAULT_AL_BACKLOG_CSV)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    closure = build_closure(args.a30_queue_json)
    if closure.get("errors"):
        print(json.dumps(closure, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    report = write_outputs(
        closure,
        policy_json_path=args.policy_json,
        closure_queue_json_path=args.closure_queue_json,
        closure_queue_csv_path=args.closure_queue_csv,
        al_backlog_csv_path=args.al_backlog_csv,
        report_json_path=args.report_json,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
