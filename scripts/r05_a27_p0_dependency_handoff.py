#!/usr/bin/env python3
"""Gate fail-closed cho bàn giao catalog/reviewer/dependency R05-A27.

Operator chỉ chạy local. Nó kết hợp kết quả semantic identity A24, hàng đợi
review 12 tài liệu, hàng đợi OCR năm trang, quyết định catalog có người chịu
trách nhiệm, blocker canonical và contract source đã triển khai. Operator không
phê duyệt nội dung GMP và không ghi Supabase, n8n hoặc Git remote.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from r05_a24_authoritative_corpus_identity_gate import build_report as build_a24_report


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_A12_REPORT = ROOT / "work/r05_a12_light_pdf_probe_live_report.json"
DEFAULT_LOCAL_MAPPING = ROOT / "work/r05_a25_actual_filename_mapping_required.csv"
DEFAULT_CATALOG_DECISIONS = ROOT / "work/r05_a27_catalog_binding_decisions.csv"
DEFAULT_CORPUS_REVIEW = ROOT / "work/r05_a26_blk004_corpus_review_queue.csv"
DEFAULT_OCR_REVIEW = ROOT / "work/r05_a26_ocr_page_review_queue.csv"
DEFAULT_PROGRESS = ROOT / "PROJECT_PROGRESS.md"
DEFAULT_OUTPUT = ROOT / "work/r05_a27_p0_dependency_handoff_report.json"

MIGRATION_027 = ROOT / "supabase/migrations/20260629191000_027_immutable_document_versions.sql"
MIGRATION_029 = ROOT / "supabase/migrations/20260629222000_029_hybrid_search_version_gate.sql"
DEPLOY_MIGRATIONS = ROOT / "supabase/migrations"
MASTER_SCHEMA_DRAFT = ROOT / "supabase/schema-contracts/p0-master-schema-draft.sql"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
AI_IDENTITY_RE = re.compile(r"\b(ai|codex|chatgpt|claude|bot|automation)\b", re.IGNORECASE)
ACCOUNTABLE_REVIEW_STATUS = "COMPLETED_ACCOUNTABLE_HUMAN_REVIEW"
ACCEPTED_REVIEW_DECISION = "APPROVED"
APPROVED_CATALOG_STATUS = "APPROVED_ACCOUNTABLE_CATALOG_DECISION"
DIRECT_BIND_ACTION = "BIND_EXISTING_LOGICAL_DOCUMENT"
SEPARATE_REFERENCE_ACTION = "CREATE_SEPARATE_REFERENCE_RECORD"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], [f"Thiếu CSV: {path}"]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            {str(key): (value or "").strip() for key, value in row.items()}
            for row in reader
        ]
        fields = list(reader.fieldnames or [])
    return rows, fields


def valid_accountable_human(name: str, role: str) -> bool:
    return bool(name and role and not AI_IDENTITY_RE.search(name) and not AI_IDENTITY_RE.search(role))


def valid_zoned_timestamp(value: str) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_catalog_decisions(
    path: Path,
    expected_hashes: dict[str, str],
) -> dict[str, Any]:
    rows, fields = read_csv(path)
    required = {
        "original_file_name",
        "source_sha256",
        "source_identity_class",
        "proposed_catalog_action",
        "target_document_code",
        "semantic_equivalence_decision",
        "decision_owner_name",
        "decision_owner_role",
        "decided_at",
        "decision_status",
        "decision_basis",
    }
    errors: list[str] = []
    missing_fields = sorted(required - set(fields))
    if missing_fields:
        errors.append("CSV quyết định catalog thiếu cột: " + ", ".join(missing_fields) + ".")
    if len(rows) != 12:
        errors.append(f"CSV quyết định catalog phải có đúng 12 dòng; hiện có {len(rows)}.")

    seen_names: set[str] = set()
    completed = 0
    accepted_direct_bindings = 0
    approved_separate_references = 0
    external_direct_binding_attempts = 0
    for index, row in enumerate(rows, start=2):
        name = row.get("original_file_name", "")
        digest = row.get("source_sha256", "").lower()
        identity_class = row.get("source_identity_class", "").upper()
        action = row.get("proposed_catalog_action", "").upper()
        status = row.get("decision_status", "").upper()
        owner_name = row.get("decision_owner_name", "")
        owner_role = row.get("decision_owner_role", "")
        decided_at = row.get("decided_at", "")
        basis = row.get("decision_basis", "")
        semantic = row.get("semantic_equivalence_decision", "").upper()
        target_code = row.get("target_document_code", "")

        if not name or name in seen_names:
            errors.append(f"Dòng catalog {index}: original_file_name thiếu hoặc trùng {name!r}.")
        seen_names.add(name)
        if not SHA256_RE.fullmatch(digest):
            errors.append(f"Dòng catalog {index}: source_sha256 không hợp lệ cho {name or '<thiếu>'}.")
        elif name in expected_hashes and expected_hashes[name] != digest:
            errors.append(f"Dòng catalog {index}: SHA-256 nguồn không khớp hàng đợi A26 cho {name}.")
        if action == DIRECT_BIND_ACTION and identity_class == "EXTERNAL_STANDARD_OR_GUIDE":
            external_direct_binding_attempts += 1
            errors.append(
                f"Dòng catalog {index}: tài liệu tham chiếu ngoài {name} không thể gắn trực "
                "tiếp vào version SOP nội bộ hiện có."
            )

        if status != APPROVED_CATALOG_STATUS:
            continue
        completed += 1
        if not valid_accountable_human(owner_name, owner_role):
            errors.append(f"Dòng catalog {index}: bắt buộc có danh tính người chịu trách nhiệm.")
        if not valid_zoned_timestamp(decided_at):
            errors.append(f"Dòng catalog {index}: decided_at phải là timestamp ISO có múi giờ.")
        if not basis:
            errors.append(f"Dòng catalog {index}: bắt buộc có decision_basis.")
        if action == DIRECT_BIND_ACTION:
            if not target_code or semantic != "CONFIRMED_SAME_LOGICAL_DOCUMENT":
                errors.append(
                    f"Dòng catalog {index}: gắn trực tiếp cần target code và "
                    "CONFIRMED_SAME_LOGICAL_DOCUMENT."
                )
            else:
                accepted_direct_bindings += 1
        elif action == SEPARATE_REFERENCE_ACTION:
            approved_separate_references += 1
        else:
            errors.append(f"Dòng catalog {index}: action đã duyệt {action!r} không được phép.")

    missing_queue_files = sorted(set(expected_hashes) - seen_names)
    unexpected_files = sorted(seen_names - set(expected_hashes))
    if missing_queue_files:
        errors.append("CSV quyết định catalog thiếu file A26: " + ", ".join(missing_queue_files) + ".")
    if unexpected_files:
        errors.append("CSV quyết định catalog có file ngoài dự kiến: " + ", ".join(unexpected_files) + ".")

    return {
        "path": str(path),
        "row_count": len(rows),
        "completed_accountable_decisions": completed,
        "accepted_direct_existing_document_bindings": accepted_direct_bindings,
        "approved_separate_reference_records": approved_separate_references,
        "external_direct_binding_attempts": external_direct_binding_attempts,
        "pending_decisions": max(len(rows) - completed, 0),
        "errors": errors,
        "ready_for_existing_document_binding": (
            len(rows) == 12 and accepted_direct_bindings == 12 and not errors
        ),
    }


def validate_review_queue(path: Path, *, expected_rows: int, page_queue: bool) -> dict[str, Any]:
    rows, fields = read_csv(path)
    required = {
        "file_name",
        "source_sha256",
        "reviewer_name",
        "reviewer_role",
        "review_status",
        "reviewed_at",
        "reviewer_decision",
        "reviewer_notes",
        "auto_approve",
    }
    if page_queue:
        required.add("page_number")
    else:
        required.add("mapping_status")

    errors: list[str] = []
    missing_fields = sorted(required - set(fields))
    if missing_fields:
        errors.append("CSV review thiếu cột: " + ", ".join(missing_fields) + ".")
    if len(rows) != expected_rows:
        errors.append(f"CSV review phải có đúng {expected_rows} dòng; hiện có {len(rows)}.")

    accepted = 0
    completed = 0
    human_identities: set[tuple[str, str]] = set()
    seen_keys: set[tuple[str, str]] = set()
    hashes: dict[str, str] = {}
    for index, row in enumerate(rows, start=2):
        name = row.get("file_name", "")
        digest = row.get("source_sha256", "").lower()
        page = row.get("page_number", "") if page_queue else "document"
        key = (name, page)
        if not name or key in seen_keys:
            errors.append(f"Dòng review {index}: review key thiếu hoặc trùng {key!r}.")
        seen_keys.add(key)
        if not SHA256_RE.fullmatch(digest):
            errors.append(f"Dòng review {index}: source_sha256 không hợp lệ cho {name or '<thiếu>'}.")
        elif name in hashes and hashes[name] != digest:
            errors.append(f"Dòng review {index}: SHA-256 nguồn không nhất quán cho {name}.")
        else:
            hashes[name] = digest
        if row.get("auto_approve", "").upper() != "FALSE":
            errors.append(f"Dòng review {index}: auto_approve bắt buộc giữ FALSE.")

        status = row.get("review_status", "").upper()
        decision = row.get("reviewer_decision", "").upper()
        if status != ACCOUNTABLE_REVIEW_STATUS:
            continue
        completed += 1
        reviewer_name = row.get("reviewer_name", "")
        reviewer_role = row.get("reviewer_role", "")
        if not valid_accountable_human(reviewer_name, reviewer_role):
            errors.append(f"Dòng review {index}: bắt buộc có danh tính reviewer con người chịu trách nhiệm.")
        else:
            human_identities.add((reviewer_name, reviewer_role))
        if not valid_zoned_timestamp(row.get("reviewed_at", "")):
            errors.append(f"Dòng review {index}: reviewed_at phải là timestamp ISO có múi giờ.")
        if not row.get("reviewer_notes", ""):
            errors.append(f"Dòng review {index}: reviewer_notes phải ghi cơ sở review.")
        mapping_ready = page_queue or row.get("mapping_status", "").upper() == "AUTHORITATIVE_CONFIRMED"
        if decision == ACCEPTED_REVIEW_DECISION and mapping_ready:
            accepted += 1

    return {
        "path": str(path),
        "row_count": len(rows),
        "completed_accountable_reviews": completed,
        "accepted_reviews": accepted,
        "pending_reviews": max(len(rows) - completed, 0),
        "accountable_human_identities": [
            {"name": name, "role": role} for name, role in sorted(human_identities)
        ],
        "hashes_by_file": hashes,
        "errors": errors,
        "ready": len(rows) == expected_rows and accepted == expected_rows and not errors,
    }


def parse_blockers(progress_path: Path) -> dict[str, dict[str, str]]:
    if not progress_path.exists():
        return {}
    blockers: dict[str, dict[str, str]] = {}
    for line in progress_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| BLK-"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        blockers[cells[0]] = {"severity": cells[1], "status": cells[5]}
    return blockers


def source_contract_checks() -> dict[str, Any]:
    migration_027 = MIGRATION_027.read_text(encoding="utf-8")
    migration_029 = MIGRATION_029.read_text(encoding="utf-8")
    draft = MASTER_SCHEMA_DRAFT.read_text(encoding="utf-8")
    deploy_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(DEPLOY_MIGRATIONS.glob("*.sql"))
    )
    return {
        "legacy_versions_are_fail_closed_and_cannot_receive_binary_identity": (
            "document_versions_legacy_fail_closed_check" in migration_027
            and "legacy_backfill_027" in migration_027
            and "binary_sha256 is null" in migration_027
        ),
        "new_ingest_version_required_for_verified_binary_lineage": (
            "ingest version bắt buộc có raw_file_id" in migration_027
            and "identity/source/binary provenance của version không được sửa" in migration_027
        ),
        "hybrid_search_uses_text_version_join": (
            "dv.version_label = dc.document_version" in migration_029
        ),
        "chunk_document_version_fk_exists_in_architecture_draft": (
            "document_chunks_document_version_id_fkey" in draft
        ),
        "chunk_document_version_fk_has_deploy_migration": (
            "document_chunks_document_version_id_fkey" in deploy_text
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    a24 = build_a24_report(args.corpus_dir, args.a12_report, args.local_mapping_csv)
    corpus_review = validate_review_queue(args.corpus_review_csv, expected_rows=12, page_queue=False)
    ocr_review = validate_review_queue(args.ocr_review_csv, expected_rows=5, page_queue=True)
    catalog = validate_catalog_decisions(
        args.catalog_decisions_csv,
        corpus_review["hashes_by_file"],
    )
    blockers = parse_blockers(args.progress)
    contracts = source_contract_checks()

    cross_queue_errors: list[str] = []
    for name, digest in ocr_review["hashes_by_file"].items():
        if corpus_review["hashes_by_file"].get(name) != digest:
            cross_queue_errors.append(
                f"SHA-256 hàng đợi trang OCR của {name} không khớp hàng đợi review corpus."
            )

    identity_ready = bool(a24["ok"]) and catalog["ready_for_existing_document_binding"]
    human_review_ready = corpus_review["ready"] and ocr_review["ready"] and not cross_queue_errors
    local_handoff_ready = identity_ready and human_review_ready

    critical_findings: list[str] = []
    if a24["summary"].get("source_identity_marker_records", 0):
        critical_findings.append(
            "File ISO/PDA/ISPE/reference bên ngoài không thể được nâng thành current version "
            "của SOP nội bộ chỉ bằng một mapping manifest chung."
        )
    if not contracts["chunk_document_version_fk_has_deploy_migration"]:
        critical_findings.append(
            "Deploy migration lane chưa có FK document_chunks.document_version_id dù bản "
            "thiết kế yêu cầu; evidence citation đúng immutable version của BLK-006 phải mở."
        )
    if blockers.get("BLK-005", {}).get("status") == "CLOSED":
        critical_findings.append(
            "BLK-005 đang được đánh CLOSED từ 65 legacy-chunk embeddings, nhưng A27 yêu cầu "
            "immutable ingest version mới cho verified binary lineage. Coverage embedding "
            "phải được tái chứng nhận sau khi tập current-version/chunk thay đổi."
        )

    dependency_impacts = [
        {
            "item": "BLK-001 / WF-06 RLS canary",
            "effect": "REMAINS_VALID",
            "link": "Biên phân quyền độc lập với nội dung catalog, nhưng phải chạy lại nếu response/auth code của WF-06 thay đổi.",
        },
        {
            "item": "BLK-002 / immutable document versions",
            "effect": "FOUNDATION_VALID_NEW_VERSION_REQUIRED",
            "link": "Legacy versions cố ý immutable/fail-closed; binary được chấp nhận cần ingest version mới và current pointer có kiểm soát.",
        },
        {
            "item": "BLK-005 / 65 embeddings",
            "effect": "HISTORICAL_BASELINE_REVALIDATION_REQUIRED",
            "link": "65 embeddings chỉ phủ legacy chunks; post-binding current-version chunks phải đạt 100% eligible coverage hoặc exclusion được duyệt.",
        },
        {
            "item": "BLK-006 / runtime citation",
            "effect": "BLOCKED_BY_003_004_AND_VERSION_FK",
            "link": "Chỉ chạy citation sau khi current version authoritative, extraction đã review, chunk gắn version và retrieval PASS.",
        },
        {
            "item": "BLK-007 / U10-U15 and agent canary",
            "effect": "BLOCKED_BY_006_AND_MISSING_GATES",
            "link": "U10 retrieval/RLS, U11 citation, U13 audit/tool log, U14 eval và U15 health đều phải PASS trước agent canary.",
        },
        {
            "item": "R07-A01/A02 table/figure designs",
            "effect": "SAFE_DESIGN_ONLY_IMPLEMENTATION_BLOCKED",
            "link": "Có thể giữ contract, nhưng schema/frontend phải gắn asset vào evidence document_version/page/bbox/hash đã được chấp nhận.",
        },
    ]

    open_p0 = sorted(
        blocker_id
        for blocker_id, value in blockers.items()
        if value["severity"] == "P0" and value["status"] not in {"CLOSED", "DONE"}
    )
    decision = (
        "READY_FOR_CONTROLLED_CURRENT_VERSION_PLAN"
        if local_handoff_ready and not critical_findings
        else "FAIL_CLOSED_P0_DEPENDENCY_HANDOFF_REQUIRED"
    )
    return {
        "schema_version": 1,
        "rhythm": "R05-A27",
        "gate": "P0_CATALOG_REVIEW_DEPENDENCY_HANDOFF",
        "ok": decision == "READY_FOR_CONTROLLED_CURRENT_VERSION_PLAN",
        "decision": decision,
        "identity": {
            "a24_decision": a24["decision"],
            "a24_ok": a24["ok"],
            "a24_summary": a24["summary"],
            "catalog_decisions": catalog,
            "ready": identity_ready,
        },
        "human_review": {
            "corpus": corpus_review,
            "ocr_pages": ocr_review,
            "cross_queue_errors": cross_queue_errors,
            "ready": human_review_ready,
        },
        "source_contract_checks": contracts,
        "canonical_blockers": blockers,
        "open_p0_blockers": open_p0,
        "critical_findings": critical_findings,
        "dependency_impacts": dependency_impacts,
        "p0_closure_checklist": [
            {"id": "P0-C01", "status": "PASS" if identity_ready else "FAIL", "check": "12/12 semantic catalog/current-version identity được chấp nhận"},
            {"id": "P0-C02", "status": "PASS" if corpus_review["ready"] else "FAIL", "check": "12/12 document extraction review có người chịu trách nhiệm"},
            {"id": "P0-C03", "status": "PASS" if ocr_review["ready"] else "FAIL", "check": "5/5 bounded OCR page review có người chịu trách nhiệm"},
            {"id": "P0-C04", "status": "FAIL", "check": "Ingest version/raw/hash/parse/current pointer mới được live verify"},
            {"id": "P0-C05", "status": "FAIL", "check": "Tập current eligible chunk có version FK và 100% embedding coverage"},
            {"id": "P0-C06", "status": "FAIL", "check": "Runtime retrieval/citation đúng chunk/version PASS"},
            {"id": "P0-C07", "status": "FAIL", "check": "U10/U11/U13/U14/U15 và agent canary PASS"},
            {"id": "P0-C08", "status": "FAIL", "check": "Source/live/manifest/evidence freshness reconciliation PASS"},
        ],
        "p0_final_check_allowed": False,
        "next_allowed_steps": [
            "Lấy quyết định catalog có người chịu trách nhiệm; giữ 12 tài liệu tham chiếu ngoài tách khỏi current version SOP nội bộ.",
            "Hoàn tất hàng đợi review 12 tài liệu và năm trang với danh tính người, timestamp, quyết định và ghi chú.",
            "Sau khi local handoff PASS, chuẩn bị live plan được duyệt riêng cho raw_files/ingest version/current pointer mới và tái chứng nhận chunk/embedding.",
            "Không chạy citation runtime, U10-U15 hoặc agent canary trước khi các gate lineage/review/retrieval phía trên PASS.",
        ],
        "evidence_hashes": {
            "catalog_decisions": sha256_file(args.catalog_decisions_csv) if args.catalog_decisions_csv.exists() else None,
            "corpus_review": sha256_file(args.corpus_review_csv) if args.corpus_review_csv.exists() else None,
            "ocr_review": sha256_file(args.ocr_review_csv) if args.ocr_review_csv.exists() else None,
            "migration_027": sha256_file(MIGRATION_027),
            "migration_029": sha256_file(MIGRATION_029),
        },
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--a12-report", type=Path, default=DEFAULT_A12_REPORT)
    parser.add_argument("--local-mapping-csv", type=Path, default=DEFAULT_LOCAL_MAPPING)
    parser.add_argument("--catalog-decisions-csv", type=Path, default=DEFAULT_CATALOG_DECISIONS)
    parser.add_argument("--corpus-review-csv", type=Path, default=DEFAULT_CORPUS_REVIEW)
    parser.add_argument("--ocr-review-csv", type=Path, default=DEFAULT_OCR_REVIEW)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(args)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "open_p0_blockers": report["open_p0_blockers"],
        "critical_findings": report["critical_findings"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
