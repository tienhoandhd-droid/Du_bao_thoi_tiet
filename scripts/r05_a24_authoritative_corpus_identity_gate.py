#!/usr/bin/env python3
"""Validate authoritative-corpus identity before hash/parse closure.

R05-A24 is local-only. It reads the corrected corpus folder, compares binary
hashes against the known R05-A12 random-light sample set, and extracts bounded
metadata/text markers as source-identity evidence. Original filenames are
preserved; CRAVE document codes are bound through a separate mapping manifest.
It does not write Supabase, execute n8n, import/chunk/embed, or touch Git remote.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from r05_authoritative_corpus_intake import REQUIRED_CODES, sha256_file, validate_corpus_dir


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_A12_REPORT = ROOT / "work/r05_a12_light_pdf_probe_live_report.json"
DEFAULT_LOCAL_MAPPING = ROOT / "work/r05_a25_actual_filename_mapping_required.csv"
DEFAULT_OUTPUT = ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json"

SOURCE_IDENTITY_MARKERS = {
    "ISO_10993": re.compile(r"\bISO\s*10993\b|\bIS0\s*10993\b", re.IGNORECASE),
    "ISO_14644": re.compile(r"\bISO\s*14644\b", re.IGNORECASE),
    "ISO_8573": re.compile(r"\bISO\s*8573\b|\bISO\s*85736\b", re.IGNORECASE),
    "BS_EN_ISO": re.compile(r"\bBS\s+EN\s+ISO\b", re.IGNORECASE),
    "ISPE_OR_PHARMACEUTICAL_ENGINEERING": re.compile(
        r"\bISPE\b|\bPHARMACEUTICAL\s+ENGINEERING\b", re.IGNORECASE
    ),
    "PDA_TECHNICAL_REPORT": re.compile(
        r"\bPDA\b|\bPARENTERAL\s+DRUG\s+ASSOCIATION\b|\bTECHNICAL\s+REPORT\b|(?<![A-Z0-9])TR[\s_-]*69(?![0-9])",
        re.IGNORECASE,
    ),
    "CLEANROOM_REFERENCE": re.compile(r"\bCLEANROOM\b|\bCLEAN\s+ROOM\b", re.IGNORECASE),
    "BIOLOGICAL_EVALUATION_MEDICAL_DEVICES": re.compile(
        r"Biological\s+evaluation\s+of\s+medical\s+devices", re.IGNORECASE
    ),
    "AUTOMATING_MACO": re.compile(r"Automating\s+MACO\s+Calculations", re.IGNORECASE),
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def load_random_light_hashes(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    lookup: dict[str, dict[str, Any]] = {}
    for execution in report.get("executions", []):
        digest = execution.get("sha256")
        if isinstance(digest, str) and len(digest) == 64:
            lookup[digest] = {
                "file_name": execution.get("file_name"),
                "page_count": execution.get("page_count"),
                "sample_status": "UNVERIFIED_RANDOM_LIGHT_SAMPLE",
            }
    return lookup


def extract_pdf_identity(path: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        return {
            "metadata": {},
            "page_count": None,
            "encrypted": None,
            "first_text_sha256": None,
            "first_text_chars": 0,
            "extract_error": f"pypdf_unavailable:{exc!r}",
            "combined_identity_text": path.name,
        }

    try:
        reader = PdfReader(str(path))
        metadata = {
            str(key): str(value)
            for key, value in (reader.metadata or {}).items()
            if value is not None
        }
        text_chunks: list[str] = []
        for page in reader.pages[:2]:
            try:
                text_chunks.append(page.extract_text() or "")
            except Exception as exc:  # pragma: no cover - defensive parser boundary
                text_chunks.append(f"[extract_error:{exc!r}]")
        first_text = "\n".join(text_chunks)
        return {
            "metadata": metadata,
            "page_count": len(reader.pages),
            "encrypted": bool(reader.is_encrypted),
            "first_text_sha256": sha256_text(first_text),
            "first_text_chars": len(first_text),
            "extract_error": None,
            "combined_identity_text": " ".join([path.name, *metadata.values(), first_text]),
        }
    except Exception as exc:  # pragma: no cover - defensive parser boundary
        return {
            "metadata": {},
            "page_count": None,
            "encrypted": None,
            "first_text_sha256": None,
            "first_text_chars": 0,
            "extract_error": repr(exc),
            "combined_identity_text": path.name,
        }


def detect_reference_markers(identity_text: str) -> list[str]:
    return [
        name
        for name, pattern in SOURCE_IDENTITY_MARKERS.items()
        if pattern.search(identity_text)
    ]


def expected_code_visible(document_code: str, identity_text: str) -> bool:
    normalized = identity_text.upper().replace("_", "-")
    code = document_code.upper()
    if code in normalized:
        return True
    if code == "WHO-TRS-996":
        return "WHO" in normalized and ("TRS" in normalized or "996" in normalized)
    return False


def visible_required_codes(identity_text: str) -> list[str]:
    normalized = identity_text.upper().replace("_", "-")
    visible: list[str] = []
    for code in REQUIRED_CODES:
        if code in normalized:
            visible.append(code)
        elif code == "WHO-TRS-996" and "WHO" in normalized and ("TRS" in normalized or "996" in normalized):
            visible.append(code)
    return visible


def raw_pdf_records(corpus_dir: Path) -> list[dict[str, Any]]:
    if not corpus_dir.exists() or not corpus_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for file_path in sorted(corpus_dir.rglob("*.pdf"), key=lambda item: str(item.relative_to(corpus_dir)).lower()):
        if any(part.startswith(".") for part in file_path.relative_to(corpus_dir).parts):
            continue
        records.append(
            {
                "document_code": None,
                "relative_path": str(file_path.relative_to(corpus_dir)),
                "size_bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
                "mime_type": mimetypes.guess_type(file_path.name)[0] or "application/pdf",
                "source": "actual_filename_unmapped_pdf",
            }
        )
    return records


def build_report(
    corpus_dir: Path,
    a12_report: Path,
    local_mapping_csv: Path | None = None,
) -> dict[str, Any]:
    intake = validate_corpus_dir(corpus_dir, local_mapping_csv).as_report()
    random_light_by_hash = load_random_light_hashes(a12_report)
    intake_records = list(intake.get("records", []))
    audit_source = "strict_intake_records" if intake_records else "actual_filename_unmapped_pdfs"
    audit_records = intake_records or raw_pdf_records(corpus_dir)

    records: list[dict[str, Any]] = []
    random_light_matches = 0
    forbidden_marker_records = 0

    for intake_record in audit_records:
        file_path = corpus_dir / intake_record["relative_path"]
        identity = extract_pdf_identity(file_path)
        identity_text = identity.pop("combined_identity_text", "")
        markers = detect_reference_markers(identity_text)
        visible_codes = visible_required_codes(identity_text)
        random_light_match = random_light_by_hash.get(intake_record["sha256"])
        if random_light_match:
            random_light_matches += 1
        if markers:
            forbidden_marker_records += 1

        document_code = intake_record.get("document_code")
        code_visible = (
            expected_code_visible(document_code, identity_text)
            if isinstance(document_code, str) and document_code
            else bool(visible_codes)
        )
        authoritative_manifest_binding = (
            intake["ok"]
            and intake["mode"] == "corpus_dir_original_filename_mapping"
            and intake_record.get("identity_binding") == "authoritative_local_mapping_manifest"
        )
        if not document_code:
            identity_decision = "FAIL_CLOSED_UNMAPPED_ACTUAL_FILENAME"
        elif authoritative_manifest_binding and markers:
            identity_decision = "CATALOG_RECONCILIATION_REQUIRED_EXTERNAL_REFERENCE"
        elif authoritative_manifest_binding:
            identity_decision = "IDENTITY_CONFIRMED_BY_AUTHORITATIVE_MANIFEST"
        elif markers or random_light_match:
            identity_decision = "FAIL_CLOSED_REFERENCE_IDENTITY_REQUIRES_MANIFEST"
        else:
            identity_decision = "IDENTITY_REVIEW_REQUIRED" if code_visible else "IDENTITY_NOT_PROVEN_REVIEW_REQUIRED"

        record = {
            **intake_record,
            "page_count": identity["page_count"],
            "encrypted": identity["encrypted"],
            "metadata_title": identity["metadata"].get("/Title"),
            "metadata_author": identity["metadata"].get("/Author"),
            "metadata_producer": identity["metadata"].get("/Producer"),
            "first_text_sha256": identity["first_text_sha256"],
            "first_text_chars": identity["first_text_chars"],
            "expected_document_code_visible": code_visible,
            "visible_required_codes": visible_codes,
            "forbidden_reference_markers": markers,
            "random_light_sample_match": random_light_match,
            "extract_error": identity["extract_error"],
            "identity_decision": identity_decision,
        }
        records.append(record)

    identity_errors: list[str] = []
    identity_warnings: list[str] = []
    if not intake["ok"]:
        identity_errors.append("Authoritative corpus intake failed.")
    if audit_source == "actual_filename_unmapped_pdfs" and records:
        identity_errors.append(
            f"{len(records)} actual-filename PDF(s) were inspected but have no owner-confirmed CRAVE document_code mapping."
        )
    if random_light_matches:
        identity_warnings.append(
            f"{random_light_matches} file(s) match hashes first observed in the R05-A12 "
            "UNVERIFIED_RANDOM_LIGHT_SAMPLE; an authoritative manifest may promote the same "
            "binary without renaming it."
        )
    if forbidden_marker_records:
        identity_warnings.append(
            f"{forbidden_marker_records} file(s) contain ISO/BS/ISPE/reference-library identity "
            "markers; these are source identity evidence, not a filename error."
        )

    catalog_reconciliation_required = sum(
        1
        for record in records
        if record["identity_decision"]
        == "CATALOG_RECONCILIATION_REQUIRED_EXTERNAL_REFERENCE"
    )
    if catalog_reconciliation_required:
        identity_errors.append(
            f"{catalog_reconciliation_required} external reference file(s) require a separate "
            "catalog decision; a generic owner mapping manifest cannot turn ISO/PDA/ISPE "
            "references into existing internal SOP document versions."
        )

    accepted_identity_records = sum(
        1
        for record in records
        if record["identity_decision"] == "IDENTITY_CONFIRMED_BY_AUTHORITATIVE_MANIFEST"
    )
    blocking_identity_records = len(records) - accepted_identity_records
    ok = (
        bool(intake["ok"])
        and not identity_errors
        and len(records) == len(REQUIRED_CODES)
        and blocking_identity_records == 0
    )
    decision = (
        "READY_FOR_LOCAL_HASH_PARSE_REVIEW"
        if ok
        else "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH"
    )

    return {
        "schema_version": 1,
        "rhythm": "R05-A24",
        "gate": "P0_AUTHORITATIVE_CORPUS_IDENTITY_GATE",
        "ok": ok,
        "decision": decision,
        "identity_errors": identity_errors,
        "identity_warnings": identity_warnings,
        "local_mapping_csv": str(local_mapping_csv) if local_mapping_csv else None,
        "intake": {
            "ok": intake["ok"],
            "decision": intake["decision"],
            "record_count": intake["record_count"],
            "errors": intake["errors"],
            "warnings": intake["warnings"],
        },
        "summary": {
            "required_record_count": len(REQUIRED_CODES),
            "intake_record_count": intake["record_count"],
            "record_count": len(records),
            "audit_source": audit_source,
            "random_light_sample_hash_matches": random_light_matches,
            "source_identity_marker_records": forbidden_marker_records,
            "forbidden_reference_marker_records": forbidden_marker_records,
            "records_with_expected_code_visible": sum(
                1 for record in records if record["expected_document_code_visible"]
            ),
            "records_identity_fail_closed": blocking_identity_records,
            "records_confirmed_by_authoritative_manifest": accepted_identity_records,
            "records_requiring_catalog_reconciliation": catalog_reconciliation_required,
        },
        "records": records,
        "quality_controls": {
            "original_filename_preserved": True,
            "filename_code_convention_required": False,
            "authoritative_local_mapping_manifest_supported": True,
            "mapping_manifest_does_not_override_semantic_identity": True,
            "reference_markers_treated_as_source_identity_evidence": True,
            "prior_sample_status_does_not_override_later_owner_confirmation": True,
            "hash_lineage_generated_but_not_authoritative": bool(records),
            "parse_evidence_denied_for_mismatched_identity": not ok,
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
            "Keep the original filenames. For internal SOP binaries, complete a separate "
            "authoritative logical-document mapping. For ISO/PDA/ISPE references, record a "
            "separate catalog-reconciliation decision instead of mapping them onto internal "
            "SOP versions. Then rerun A24 before any Supabase or n8n closure step."
            if not ok
            else "Proceed to bounded parse/reviewer evidence and separately approved Supabase lineage linkage."
        ),
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--a12-report", type=Path, default=DEFAULT_A12_REPORT)
    parser.add_argument(
        "--local-mapping-csv",
        type=Path,
        default=DEFAULT_LOCAL_MAPPING,
        help="Optional authoritative document_code to original filename mapping manifest.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.corpus_dir, args.a12_report, args.local_mapping_csv)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "record_count": report["summary"]["record_count"],
        "random_light_sample_hash_matches": report["summary"]["random_light_sample_hash_matches"],
        "forbidden_reference_marker_records": report["summary"]["forbidden_reference_marker_records"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
