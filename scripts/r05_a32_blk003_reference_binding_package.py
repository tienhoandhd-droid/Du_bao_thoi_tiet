#!/usr/bin/env python3
"""Prepare the R05-A32 source-only BLK-003 reference binding package.

R05-A32 does not apply Supabase changes. It creates the exact local package that
must be reviewed before a later approved live run can create REF-* documents,
verified raw-file lineage, immutable ingest versions and current-version
pointers. This keeps BLK-003 fail-closed until live preflight/apply/verification
is explicitly approved and completed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1

DEFAULT_CATALOG_CSV = ROOT / "work/r05_a28_drive_native_catalog.csv"
DEFAULT_RETIREMENT_CSV = ROOT / "work/r05_a28_internal_sop_retirement_plan.csv"
DEFAULT_A31_REPORT_JSON = ROOT / "work/r05_a31_blk004_resource_policy_closure_report.json"

DEFAULT_PLAN_CSV = ROOT / "work/r05_a32_blk003_reference_binding_plan.csv"
DEFAULT_PLAN_JSON = ROOT / "work/r05_a32_blk003_reference_binding_plan.json"
DEFAULT_PREFLIGHT_SQL = ROOT / "work/r05_a32_blk003_supabase_preflight_readonly.sql"
DEFAULT_APPLY_PROPOSAL_SQL = ROOT / "work/r05_a32_blk003_supabase_apply_proposal_not_for_apply.sql"
DEFAULT_ROLLBACK_PROPOSAL_SQL = ROOT / "work/r05_a32_blk003_supabase_rollback_proposal_not_for_apply.sql"
DEFAULT_REPORT_JSON = ROOT / "work/r05_a32_blk003_reference_binding_report.json"

EXPECTED_REF_COUNT = 12
EXPECTED_RETIRE_COUNT = 10
EXPECTED_OPEN_P0_AFTER_A31 = ["BLK-003", "BLK-005", "BLK-006", "BLK-007"]

PLAN_FIELDS = [
    "binding_id",
    "document_code",
    "document_title",
    "original_file_name",
    "drive_file_id",
    "drive_parent_path",
    "drive_web_view_link",
    "mime_type",
    "size_bytes",
    "binary_sha256",
    "source_organization",
    "source_review_gate",
    "technical_evidence_status",
    "extraction_path",
    "raw_file_action",
    "document_action",
    "version_label",
    "version_action",
    "current_pointer_action",
    "approved_for_ai_use",
    "document_version_hash_status",
    "document_version_license_status",
    "document_version_parse_status",
    "document_version_index_status",
    "production_retrieval",
    "live_required",
    "verification_required",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    """Return repo-relative paths when possible, otherwise an absolute path."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "có"}


def make_version_label(binary_sha256: str) -> str:
    return f"ref-a32-20260630-{binary_sha256[:12]}"


def validate_inputs(
    catalog_rows: list[dict[str, str]],
    retirement_rows: list[dict[str, str]],
    a31_report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if len(catalog_rows) != EXPECTED_REF_COUNT:
        errors.append(f"Catalog A28 phải có {EXPECTED_REF_COUNT} REF rows; hiện có {len(catalog_rows)}.")
    if len(retirement_rows) != EXPECTED_RETIRE_COUNT:
        errors.append(
            f"Retirement plan A28 phải có {EXPECTED_RETIRE_COUNT} internal SOP rows; hiện có {len(retirement_rows)}."
        )

    ref_codes = [row.get("document_code", "") for row in catalog_rows]
    drive_ids = [row.get("drive_file_id", "") for row in catalog_rows]
    hashes = [row.get("binary_sha256", "") for row in catalog_rows]
    if any(not code.startswith("REF-") for code in ref_codes):
        errors.append("Catalog binding chỉ được chứa document_code bắt đầu bằng REF-.")
    if len(set(ref_codes)) != len(ref_codes):
        errors.append("Catalog binding có document_code trùng.")
    if any(not drive_id for drive_id in drive_ids) or len(set(drive_ids)) != len(drive_ids):
        errors.append("Catalog binding có Drive file ID thiếu hoặc trùng.")
    if any(len(item) != 64 for item in hashes) or len(set(hashes)) != len(hashes):
        errors.append("Catalog binding có SHA-256 thiếu/sai định dạng hoặc trùng.")

    for row in catalog_rows:
        if parse_bool(row.get("approved_for_ai_use")):
            errors.append(f"{row.get('document_code')}: A28 catalog không được approved_for_ai_use.")
        if row.get("production_retrieval") != "DENY_UNTIL_VERSION_REVIEW_EMBED_CITATION_PASS":
            errors.append(f"{row.get('document_code')}: production_retrieval phải tiếp tục deny.")

    expected_retire_codes = [f"GMP-SOP-{index:03d}" for index in range(1, 11)]
    actual_retire_codes = [row.get("document_code", "") for row in retirement_rows]
    if actual_retire_codes != expected_retire_codes:
        errors.append("Retirement plan phải đúng 10 mã GMP-SOP-001..010 theo thứ tự.")
    for row in retirement_rows:
        if parse_bool(row.get("hard_delete")):
            errors.append(f"{row.get('document_code')}: retire plan không được hard delete.")
        if row.get("current_version_action") != "PRESERVE_IMMUTABLE_EVIDENCE":
            errors.append(f"{row.get('document_code')}: phải preserve immutable current/version evidence.")

    if a31_report.get("decision") != "BLK004_CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED_SOURCE_ONLY":
        errors.append("A31 prerequisite chưa đóng BLK-004 theo policy resource-aware.")
    summary = a31_report.get("summary", {})
    if summary.get("blk004_status_after_a31") != "CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED":
        errors.append("A31 summary chưa xác nhận BLK-004 CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED.")
    if summary.get("document_pass_count") != 12 or summary.get("ocr_closed_for_blk004_count") != 5:
        errors.append("A31 summary chưa đủ 12 document pass và 5 OCR page closure.")
    if summary.get("open_p0_after_blk004_closure") != EXPECTED_OPEN_P0_AFTER_A31:
        errors.append("A31 open P0 list không khớp BLK-003/005/006/007.")
    if summary.get("production_ai_use_allowed") is not False:
        errors.append("A31 không được mở production AI use.")

    return errors


def build_binding_rows(catalog_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(catalog_rows, start=1):
        extraction_path = row.get("extraction_path", "")
        parse_status = "partial" if "OCR" in extraction_path.upper() else "success"
        binary_sha256 = row.get("binary_sha256", "").lower()
        rows.append(
            {
                "binding_id": f"R05-A32-BIND-{index:03d}",
                "document_code": row.get("document_code", ""),
                "document_title": row.get("document_title", ""),
                "original_file_name": row.get("original_file_name", ""),
                "drive_file_id": row.get("drive_file_id", ""),
                "drive_parent_path": row.get("drive_parent_path", ""),
                "drive_web_view_link": row.get("drive_web_view_link", ""),
                "mime_type": row.get("mime_type", ""),
                "size_bytes": int(row.get("size_bytes") or 0),
                "binary_sha256": binary_sha256,
                "source_organization": row.get("source_organization", ""),
                "source_review_gate": "A31_BLK004_RESOURCE_AWARE_CLOSED_BUT_AI_USE_DENIED",
                "technical_evidence_status": row.get("technical_evidence_status", ""),
                "extraction_path": extraction_path,
                "raw_file_action": "CREATE_OR_VERIFY_RAW_FILE_HASH_STATUS_VERIFIED",
                "document_action": "CREATE_REF_DOCUMENT_IF_ABSENT_WITH_NON_RETRIEVAL_STATUS",
                "version_label": make_version_label(binary_sha256),
                "version_action": "CREATE_IMMUTABLE_INGEST_VERSION_FROM_VERIFIED_RAW_FILE",
                "current_pointer_action": "SET_DOCUMENT_CURRENT_VERSION_TO_NEW_REF_INGEST_VERSION",
                "approved_for_ai_use": "FALSE",
                "document_version_hash_status": "verified",
                "document_version_license_status": "metadata_only",
                "document_version_parse_status": parse_status,
                "document_version_index_status": "excluded",
                "production_retrieval": "DENY_UNTIL_BLK005_BLK006_BLK007_PASS",
                "live_required": "TRUE",
                "verification_required": "RAW_FILE_VERSION_CURRENT_POINTER_LIVE_VERIFY",
            }
        )
    return rows


def build_retirement_rows(retirement_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "document_code": row.get("document_code", ""),
            "transition_action": row.get("transition_action", ""),
            "target_document_status": row.get("target_document_status", ""),
            "target_approved_for_ai_use": "FALSE",
            "current_version_action": row.get("current_version_action", ""),
            "chunk_action": row.get("chunk_action", ""),
            "document_access_action": row.get("document_access_action", ""),
            "hard_delete": "FALSE",
            "rollback_action": "RESTORE_PRE_A32_STATUS_FROM_LIVE_SNAPSHOT_AND_REACTIVATE_ACCESS_IF_WAS_ACTIVE",
            "live_required": "TRUE",
        }
        for row in retirement_rows
    ]


def csv_literal(values: list[str]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def build_preflight_sql(binding_rows: list[dict[str, Any]], retirement_rows: list[dict[str, Any]]) -> str:
    ref_codes = [str(row["document_code"]) for row in binding_rows]
    retire_codes = [str(row["document_code"]) for row in retirement_rows]
    drive_ids = [str(row["drive_file_id"]) for row in binding_rows]
    hashes = [str(row["binary_sha256"]) for row in binding_rows]
    return f"""-- R05-A32 / BLK-003 READ-ONLY PREFLIGHT
-- Scope: verify live schema/state before any approved REF-* binding run.
-- This file is read-only: no INSERT/UPDATE/DELETE/DDL.

select
  'required_table_presence' as check_name,
  to_regclass('public.documents') is not null as documents_exists,
  to_regclass('public.raw_files') is not null as raw_files_exists,
  to_regclass('public.document_versions') is not null as document_versions_exists,
  to_regclass('public.document_chunks') is not null as document_chunks_exists,
  to_regclass('public.document_access') is not null as document_access_exists;

select
  t.typname as enum_name,
  array_agg(e.enumlabel order by e.enumsortorder) as enum_values
from pg_type t
join pg_namespace n on n.oid = t.typnamespace
join pg_enum e on e.enumtypid = t.oid
where n.nspname = 'public'
  and t.typname in ('document_status', 'document_type', 'source_type', 'language_code')
group by t.typname
order by t.typname;

select
  c.table_name,
  c.column_name,
  c.data_type,
  c.udt_schema,
  c.udt_name,
  c.is_nullable,
  c.column_default
from information_schema.columns c
where c.table_schema = 'public'
  and c.table_name in ('documents', 'raw_files', 'document_versions', 'document_chunks', 'document_access')
order by c.table_name, c.ordinal_position;

select
  'existing_ref_documents' as check_name,
  count(*) as existing_ref_document_count,
  array_agg(d.document_code order by d.document_code) as existing_ref_document_codes
from public.documents d
where d.document_code in ({csv_literal(ref_codes)});

select
  'existing_raw_drive_ids' as check_name,
  count(*) as existing_raw_drive_id_count,
  array_agg(r.drive_file_id order by r.drive_file_id) as existing_raw_drive_ids
from public.raw_files r
where r.drive_file_id in ({csv_literal(drive_ids)});

select
  'existing_raw_hashes' as check_name,
  count(*) as existing_raw_hash_count,
  array_agg(r.binary_sha256 order by r.binary_sha256) as existing_raw_hashes
from public.raw_files r
where r.binary_sha256 in ({csv_literal(hashes)});

select
  'legacy_sop_retire_candidates' as check_name,
  d.document_code,
  d.document_title,
  d.status::text as document_status,
  d.approved_for_ai_use,
  d.current_version_id,
  count(distinct dv.id) as version_count,
  count(distinct dc.id) as chunk_count,
  count(distinct da.id) filter (where da.is_active) as active_access_count
from public.documents d
left join public.document_versions dv on dv.document_id = d.id
left join public.document_chunks dc on dc.document_id = d.id
left join public.document_access da on da.document_id = d.id
where d.document_code in ({csv_literal(retire_codes)})
group by d.document_code, d.document_title, d.status, d.approved_for_ai_use, d.current_version_id
order by d.document_code;

select
  'current_version_integrity' as check_name,
  count(*) filter (where d.current_version_id is null) as missing_current_pointer,
  count(*) filter (where dv.id is null and d.current_version_id is not null) as broken_current_pointer,
  count(*) filter (where dv.id is not null and dv.document_id is distinct from d.id) as wrong_document_pointer
from public.documents d
left join public.document_versions dv on dv.id = d.current_version_id
where d.document_code in ({csv_literal(ref_codes + retire_codes)});
"""


def build_apply_proposal_sql(binding_rows: list[dict[str, Any]], retirement_rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "action": "R05-A32",
            "binding_rows": binding_rows,
            "retirement_rows": retirement_rows,
        },
        ensure_ascii=False,
        indent=2,
    )
    return f"""-- R05-A32 / BLK-003 SUPABASE APPLY PROPOSAL — NOT FOR APPLY
-- This proposal is intentionally guarded. Do not run unless the owner approves
-- the exact change set after the read-only preflight output is reviewed.
--
-- Required live order:
--   1) Run r05_a32_blk003_supabase_preflight_readonly.sql and review output.
--   2) Confirm documents enum/candidate non-retrieval status from live schema.
--   3) Create REF-* documents only if absent.
--   4) Create/verify raw_files with hash_status='verified' and status='verified'.
--   5) Create document_versions record_origin='ingest' from verified raw_file_id.
--   6) Set documents.current_version_id to the newly created ingest version.
--   7) Retire GMP-SOP-001..010 reversibly; no hard delete.
--   8) Re-run verification queries, then only after PASS proceed to BLK-005.
--
-- The JSON payload below is the source-of-truth package for the later live SQL.

do $guard$
begin
  if current_setting('crave.a32_apply_approved', true) is distinct from 'true' then
    raise exception 'R05-A32 is source-only. Set crave.a32_apply_approved=true only in an explicitly approved live run.';
  end if;
end
$guard$;

-- Payload for approved live operator:
select $r05_a32_payload$
{payload}
$r05_a32_payload$::jsonb as r05_a32_approved_payload;

-- DML is deliberately not expanded in this source-only artifact because the
-- live documents enum/candidate status and non-null/default column shape must be
-- confirmed by the preflight output first. The later live operator must consume
-- the payload above and satisfy the immutable-version constraints from CRAVE-027:
-- raw_files.status='verified', raw_files.hash_status='verified',
-- document_versions.record_origin='ingest', same document_id/raw_file_id and
-- same binary_sha256 before current_version_id is updated.
"""


def build_rollback_proposal_sql(binding_rows: list[dict[str, Any]], retirement_rows: list[dict[str, Any]]) -> str:
    ref_codes = [str(row["document_code"]) for row in binding_rows]
    retire_codes = [str(row["document_code"]) for row in retirement_rows]
    return f"""-- R05-A32 / BLK-003 ROLLBACK PROPOSAL — NOT FOR APPLY
-- Rollback must be generated from a live pre-apply snapshot. Do not run this
-- file directly. It documents the required safe rollback semantics.

-- REF rows created by A32 must be rollback-eligible only when:
--   - document_code is in ({csv_literal(ref_codes)});
--   - no document_chunks / ai_query_sources / audit consumers reference the new version;
--   - current_version_id points to the A32-created version;
--   - approved_for_ai_use is still false and index_status is not ready.

-- Retired SOP rows must be restored from the pre-apply snapshot for:
--   {csv_literal(retire_codes)}
--
-- No hard delete is allowed for legacy SOP evidence. Any deletion of A32-created
-- REF rows must be blocked if downstream consumers exist; otherwise mark them
-- archived/non-retrieval and preserve audit evidence.
"""


def build_package(
    *,
    catalog_csv: Path = DEFAULT_CATALOG_CSV,
    retirement_csv: Path = DEFAULT_RETIREMENT_CSV,
    a31_report_json: Path = DEFAULT_A31_REPORT_JSON,
) -> dict[str, Any]:
    missing_inputs = [str(path) for path in (catalog_csv, retirement_csv, a31_report_json) if not path.exists()]
    if missing_inputs:
        return {
            "schema_version": SCHEMA_VERSION,
            "gate": "R05_A32_BLK003_REFERENCE_BINDING_PACKAGE",
            "decision": "FAIL_CLOSED_MISSING_INPUT",
            "errors": [f"Missing input: {path}" for path in missing_inputs],
            "warnings": [],
            "binding_rows": [],
            "retirement_rows": [],
        }

    catalog_rows = read_csv(catalog_csv)
    retirement_source_rows = read_csv(retirement_csv)
    a31_report = read_json(a31_report_json)
    errors = validate_inputs(catalog_rows, retirement_source_rows, a31_report)

    binding_rows = build_binding_rows(catalog_rows)
    retirement_rows = build_retirement_rows(retirement_source_rows)
    preflight_sql = build_preflight_sql(binding_rows, retirement_rows)
    apply_proposal_sql = build_apply_proposal_sql(binding_rows, retirement_rows)
    rollback_proposal_sql = build_rollback_proposal_sql(binding_rows, retirement_rows)

    decision = (
        "BLK003_READY_FOR_LIVE_PREFLIGHT_AND_APPROVAL_SOURCE_ONLY"
        if not errors
        else "FAIL_CLOSED_BINDING_PACKAGE_INVALID"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "gate": "R05_A32_BLK003_REFERENCE_BINDING_PACKAGE",
        "decision": decision,
        "errors": errors,
        "warnings": [
            "A32 is source-only; BLK-003 remains OPEN until approved live preflight/apply/verify PASS.",
            "Do not proceed to BLK-005 embedding recertification until BLK-003 live current-version lineage is verified.",
            "A31 BLK-004 closure does not authorize production AI/retrieval/indexing.",
        ],
        "source": {
            "catalog_csv": display_path(catalog_csv),
            "catalog_sha256": sha256_file(catalog_csv),
            "retirement_csv": display_path(retirement_csv),
            "retirement_sha256": sha256_file(retirement_csv),
            "a31_report_json": display_path(a31_report_json),
            "a31_report_sha256": sha256_file(a31_report_json),
        },
        "summary": {
            "reference_binding_count": len(binding_rows),
            "internal_sop_retirement_count": len(retirement_rows),
            "blk003_status_after_a32": "OPEN_READY_FOR_LIVE_PREFLIGHT_AND_APPROVAL",
            "blk004_prerequisite": "CLOSED_RESOURCE_AWARE_POLICY_ACCEPTED",
            "next_allowed_after_blk003_live_verify": "BLK-005_EMBEDDING_RECERTIFICATION",
            "production_ai_use_allowed": False,
            "production_retrieval": "DENY_UNTIL_BLK005_BLK006_BLK007_PASS",
            "open_p0_after_a32": ["BLK-003", "BLK-005", "BLK-006", "BLK-007"],
        },
        "lineage_contract": {
            "legacy_sop_versions_mutated": False,
            "legacy_sop_hard_delete_allowed": False,
            "reference_documents_must_use_ref_codes": True,
            "raw_file_verified_required_before_ingest_version": True,
            "immutable_ingest_version_required": True,
            "current_version_pointer_required": True,
            "live_verification_required": True,
            "embedding_recertification_deferred_to_blk005": True,
            "citation_runtime_deferred_to_blk006": True,
            "agent_gate_deferred_to_blk007": True,
        },
        "p0_check_effect": [
            {"id": "P0-C01", "status": "LOCAL_READY", "check": "12/12 REF semantic catalog identities packaged for live binding"},
            {"id": "P0-C02", "status": "PASS_LOCAL_A31", "check": "12/12 document reviews accepted by QA Hoàn"},
            {"id": "P0-C03", "status": "PASS_RESOURCE_AWARE_A31", "check": "5/5 OCR pages closed for BLK-004 under AL/backlog policy"},
            {"id": "P0-C04", "status": "FAIL_LIVE_REQUIRED", "check": "Raw/hash/parse/new ingest version/current pointer live verified"},
            {"id": "P0-C05", "status": "BLOCKED_BY_BLK003", "check": "Current-version chunk embedding recertification"},
            {"id": "P0-C06", "status": "BLOCKED_BY_BLK003_AND_BLK005", "check": "Runtime retrieval/citation evidence"},
            {"id": "P0-C07", "status": "BLOCKED_BY_BLK003_TO_BLK006", "check": "U10-U15 and agent canary"},
            {"id": "P0-C08", "status": "FAIL_LIVE_REQUIRED", "check": "Source/live/manifest/evidence freshness reconciliation"},
        ],
        "remote_operations": {"drive": [], "git": [], "n8n": [], "supabase": []},
        "binding_rows": binding_rows,
        "retirement_rows": retirement_rows,
        "sql_artifacts": {
            "preflight_readonly_sha256": sha256_text(preflight_sql),
            "apply_proposal_sha256": sha256_text(apply_proposal_sql),
            "rollback_proposal_sha256": sha256_text(rollback_proposal_sql),
        },
        "_generated_sql": {
            "preflight": preflight_sql,
            "apply_proposal": apply_proposal_sql,
            "rollback_proposal": rollback_proposal_sql,
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    package: dict[str, Any],
    *,
    plan_csv: Path = DEFAULT_PLAN_CSV,
    plan_json: Path = DEFAULT_PLAN_JSON,
    preflight_sql: Path = DEFAULT_PREFLIGHT_SQL,
    apply_proposal_sql: Path = DEFAULT_APPLY_PROPOSAL_SQL,
    rollback_proposal_sql: Path = DEFAULT_ROLLBACK_PROPOSAL_SQL,
    report_json: Path = DEFAULT_REPORT_JSON,
) -> dict[str, Any]:
    sql = package.pop("_generated_sql")
    write_csv(plan_csv, package.get("binding_rows", []), PLAN_FIELDS)
    plan_json.parent.mkdir(parents=True, exist_ok=True)
    plan_json.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "gate": package.get("gate"),
                "decision": package.get("decision"),
                "summary": package.get("summary"),
                "binding_rows": package.get("binding_rows", []),
                "retirement_rows": package.get("retirement_rows", []),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    preflight_sql.write_text(sql["preflight"], encoding="utf-8")
    apply_proposal_sql.write_text(sql["apply_proposal"], encoding="utf-8")
    rollback_proposal_sql.write_text(sql["rollback_proposal"], encoding="utf-8")

    report = {
        key: value
        for key, value in package.items()
        if key not in {"binding_rows", "retirement_rows"}
    }
    report["outputs"] = {
        "plan_csv": display_path(plan_csv),
        "plan_json": display_path(plan_json),
        "preflight_sql": display_path(preflight_sql),
        "apply_proposal_sql": display_path(apply_proposal_sql),
        "rollback_proposal_sql": display_path(rollback_proposal_sql),
        "report_json": display_path(report_json),
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-csv", type=Path, default=DEFAULT_CATALOG_CSV)
    parser.add_argument("--retirement-csv", type=Path, default=DEFAULT_RETIREMENT_CSV)
    parser.add_argument("--a31-report-json", type=Path, default=DEFAULT_A31_REPORT_JSON)
    parser.add_argument("--plan-csv", type=Path, default=DEFAULT_PLAN_CSV)
    parser.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN_JSON)
    parser.add_argument("--preflight-sql", type=Path, default=DEFAULT_PREFLIGHT_SQL)
    parser.add_argument("--apply-proposal-sql", type=Path, default=DEFAULT_APPLY_PROPOSAL_SQL)
    parser.add_argument("--rollback-proposal-sql", type=Path, default=DEFAULT_ROLLBACK_PROPOSAL_SQL)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    args = parser.parse_args()

    package = build_package(
        catalog_csv=args.catalog_csv,
        retirement_csv=args.retirement_csv,
        a31_report_json=args.a31_report_json,
    )
    if package["decision"].startswith("FAIL_CLOSED"):
        print(json.dumps({k: v for k, v in package.items() if k != "_generated_sql"}, ensure_ascii=False, indent=2))
        return 1

    report = write_outputs(
        package,
        plan_csv=args.plan_csv,
        plan_json=args.plan_json,
        preflight_sql=args.preflight_sql,
        apply_proposal_sql=args.apply_proposal_sql,
        rollback_proposal_sql=args.rollback_proposal_sql,
        report_json=args.report_json,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
