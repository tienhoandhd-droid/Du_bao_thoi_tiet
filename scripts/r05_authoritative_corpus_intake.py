#!/usr/bin/env python3
"""Validate the authoritative 12-file corpus intake for R05 BLK-003/004.

This is a local-only gate. It does not download files, call Supabase, execute n8n,
or mutate any remote system. It only validates either:

- a CSV mapping from CRAVE document code to authoritative Drive file ID, or
- a corrected local corpus folder containing exactly one source file per code.

Local corpus filenames may remain byte-for-byte identical to the uploaded
originals. A separate local mapping manifest binds each original filename to a
CRAVE document code; embedding the code in the filename is only a legacy
fallback when no manifest is supplied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_CODES = tuple(
    [*(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)), "VQ-QT-003", "WHO-TRS-996"]
)
REQUIRED_CODE_SET = set(REQUIRED_CODES)

ID_COLUMNS = (
    "drive_file_id",
    "authoritative_drive_file_id",
    "required_authoritative_drive_file_id",
    "candidate_drive_id",
)
NAME_COLUMNS = ("file_name", "name", "drive_file_name", "candidate_name")
MIME_COLUMNS = ("mime_type", "drive_mime_type", "candidate_mime_type")
STATUS_COLUMNS = ("status", "decision", "mapping_status")

PLACEHOLDERS = {
    "",
    "REQUIRED",
    "REQUIRED_AFTER_DOWNLOAD",
    "REQUIRED_AFTER_PARSE",
    "AWAITING_AUTHORITATIVE_MAPPING",
    "NO_SAFE_MATCH",
    "UNVERIFIED_THEMATIC_CANDIDATE",
    "TBD",
    "TODO",
    "UNKNOWN",
    "N/A",
    "NA",
    "NONE",
}

ARCHIVE_EXTENSIONS = {
    ".7z",
    ".gz",
    ".rar",
    ".tar",
    ".tgz",
    ".zip",
}
ARCHIVE_MIME_MARKERS = ("archive", "rar", "zip", "tar", "gzip", "7z")
REJECTED_EXTENSIONS = {
    ".csv",
    ".html",
    ".json",
    ".md",
    ".txt",
    ".xml",
}
AUTHORITATIVE_STATUS = "AUTHORITATIVE_CONFIRMED"
LOCAL_MAPPING_REQUIRED_COLUMNS = {
    "document_code",
    "file_name",
    "status",
    "mapping_notes",
}
PDF_MIME_TYPE = "application/pdf"
ALLOWED_SOURCE_EXTENSIONS = {".pdf"}
FORBIDDEN_AUTHORITATIVE_BINARY_MARKERS = (
    b"AI_DRAFT_FOR_OWNER_REVIEW",
    b"DRAFT_NOT_APPROVED_FOR_GMP_USE",
)


@dataclass(frozen=True)
class IntakeResult:
    ok: bool
    mode: str
    errors: list[str]
    warnings: list[str]
    records: list[dict[str, Any]]

    def as_report(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "decision": "PASS" if self.ok else "FAIL_CLOSED",
            "mode": self.mode,
            "required_codes": list(REQUIRED_CODES),
            "record_count": len(self.records),
            "records": self.records,
            "errors": self.errors,
            "warnings": self.warnings,
            "remote_operations": {
                "supabase": [],
                "n8n": [],
                "git": [],
            },
        }


def normalize_placeholder(value: str | None) -> str:
    return (value or "").strip().upper()


def is_placeholder(value: str | None) -> bool:
    return normalize_placeholder(value) in PLACEHOLDERS


def first_present(row: dict[str, str], columns: tuple[str, ...]) -> str:
    for column in columns:
        if column in row:
            value = (row.get(column) or "").strip()
            if value:
                return value
    return ""


def looks_like_archive(name: str = "", mime_type: str = "") -> bool:
    suffix = Path(name).suffix.lower()
    normalized_mime = mime_type.lower()
    return suffix in ARCHIVE_EXTENSIONS or any(marker in normalized_mime for marker in ARCHIVE_MIME_MARKERS)


def validate_mapping_csv(path: Path) -> IntakeResult:
    errors: list[str] = []
    warnings: list[str] = []
    records: list[dict[str, Any]] = []

    if not path.exists():
        return IntakeResult(False, "mapping_csv", [f"Mapping CSV not found: {path}"], [], [])

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        errors.append("Mapping CSV is empty.")
        return IntakeResult(False, "mapping_csv", errors, warnings, records)

    fieldnames = set(rows[0].keys())
    if "document_code" not in fieldnames:
        errors.append("Mapping CSV must include a document_code column.")
    if not fieldnames.intersection(ID_COLUMNS):
        errors.append(
            "Mapping CSV must include one authoritative file ID column: "
            + ", ".join(ID_COLUMNS)
            + "."
        )
    if not fieldnames.intersection(STATUS_COLUMNS):
        errors.append("Mapping CSV must include a status column.")
    if not fieldnames.intersection(NAME_COLUMNS):
        errors.append("Mapping CSV must include a file name column.")
    if not fieldnames.intersection(MIME_COLUMNS):
        errors.append("Mapping CSV must include a MIME type column.")

    seen_codes: dict[str, int] = {}
    seen_ids: dict[str, str] = {}

    for idx, row in enumerate(rows, start=2):
        code = (row.get("document_code") or "").strip()
        drive_file_id = first_present(row, ID_COLUMNS)
        file_name = first_present(row, NAME_COLUMNS)
        mime_type = first_present(row, MIME_COLUMNS)
        status = first_present(row, STATUS_COLUMNS)

        record = {
            "document_code": code,
            "drive_file_id": drive_file_id,
            "file_name": file_name,
            "mime_type": mime_type,
            "status": status,
            "source_row": idx,
        }
        records.append(record)

        if code not in REQUIRED_CODE_SET:
            errors.append(f"Row {idx}: unexpected or missing document_code {code!r}.")
            continue

        seen_codes[code] = seen_codes.get(code, 0) + 1
        if seen_codes[code] > 1:
            errors.append(f"Row {idx}: duplicate document_code {code}.")

        if is_placeholder(drive_file_id):
            errors.append(f"Row {idx}: {code} has no authoritative Drive file ID.")
        elif drive_file_id in seen_ids and seen_ids[drive_file_id] != code:
            errors.append(
                f"Row {idx}: Drive file ID {drive_file_id!r} is reused by "
                f"{seen_ids[drive_file_id]} and {code}."
            )
        else:
            seen_ids[drive_file_id] = code

        normalized_status = status.upper()
        if normalized_status != AUTHORITATIVE_STATUS:
            errors.append(
                f"Row {idx}: {code} status must be exactly "
                f"{AUTHORITATIVE_STATUS!r}; found {status!r}."
            )

        if looks_like_archive(file_name, mime_type):
            errors.append(
                f"Row {idx}: {code} points at an archive-like file "
                f"({file_name or 'unnamed'}, {mime_type or 'unknown MIME'})."
            )
        if not file_name:
            errors.append(f"Row {idx}: {code} has no authoritative PDF file_name.")
        elif Path(file_name).suffix.lower() != ".pdf":
            errors.append(f"Row {idx}: {code} file_name must end in .pdf; found {file_name!r}.")
        if mime_type.lower() != PDF_MIME_TYPE:
            errors.append(
                f"Row {idx}: {code} mime_type must be {PDF_MIME_TYPE!r}; "
                f"found {mime_type!r}."
            )

    missing = sorted(REQUIRED_CODE_SET - set(seen_codes))
    extra_count = len(rows) - len(REQUIRED_CODES)
    if missing:
        errors.append("Missing required document codes: " + ", ".join(missing) + ".")
    if extra_count != 0:
        errors.append(f"Mapping CSV must contain exactly 12 rows; found {len(rows)}.")

    if not errors:
        warnings.append(
            "Mapping validates as authoritative intake only; controlled download, "
            "SHA-256 lineage, parse evidence and reviewer decisions are still required."
        )

    return IntakeResult(not errors, "mapping_csv", errors, warnings, sorted(records, key=lambda r: r["document_code"]))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contains_forbidden_authoritative_marker(path: Path) -> str | None:
    overlap = max(len(marker) for marker in FORBIDDEN_AUTHORITATIVE_BINARY_MARKERS) - 1
    tail = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            window = tail + chunk
            for marker in FORBIDDEN_AUTHORITATIVE_BINARY_MARKERS:
                if marker in window:
                    return marker.decode("ascii")
            tail = window[-overlap:] if overlap else b""
    return None


def code_matches_for_file(path: Path) -> list[str]:
    normalized_name = path.name.upper().replace("_", "-")
    return [code for code in REQUIRED_CODES if code in normalized_name]


def load_local_filename_mapping(
    mapping_csv: Path,
    corpus_dir: Path,
    files: list[Path],
) -> tuple[dict[str, dict[str, str]], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    mapped_by_relative_path: dict[str, dict[str, str]] = {}
    if not mapping_csv.exists():
        return {}, [f"Local filename mapping CSV not found: {mapping_csv}"], warnings

    with mapping_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = set(reader.fieldnames or [])

    missing_columns = sorted(LOCAL_MAPPING_REQUIRED_COLUMNS - fieldnames)
    if missing_columns:
        errors.append(
            "Local filename mapping CSV is missing columns: "
            + ", ".join(missing_columns)
            + "."
        )
    if len(rows) != len(REQUIRED_CODES):
        errors.append(f"Local filename mapping CSV must contain exactly 12 rows; found {len(rows)}.")

    corpus_relative_paths = {
        str(file_path.relative_to(corpus_dir)): file_path for file_path in files
    }
    seen_codes: dict[str, int] = {}
    seen_file_names: dict[str, str] = {}
    for idx, row in enumerate(rows, start=2):
        code = (row.get("document_code") or "").strip()
        file_name = (row.get("file_name") or "").strip()
        status = (row.get("status") or "").strip()
        mapping_notes = (row.get("mapping_notes") or "").strip()

        if code not in REQUIRED_CODE_SET:
            errors.append(f"Row {idx}: unexpected or missing document_code {code!r}.")
        else:
            seen_codes[code] = seen_codes.get(code, 0) + 1
            if seen_codes[code] > 1:
                errors.append(f"Row {idx}: duplicate document_code {code}.")

        if not file_name:
            errors.append(f"Row {idx}: {code or '<missing code>'} has no original file_name.")
            continue
        file_path_value = Path(file_name)
        if file_path_value.is_absolute() or ".." in file_path_value.parts:
            errors.append(f"Row {idx}: unsafe file_name path {file_name!r}.")
            continue
        if file_name in seen_file_names:
            errors.append(
                f"Row {idx}: original file_name {file_name!r} is reused by "
                f"{seen_file_names[file_name]} and {code}."
            )
        else:
            seen_file_names[file_name] = code
        if file_name not in corpus_relative_paths:
            errors.append(f"Row {idx}: mapped original file is not present in corpus: {file_name!r}.")

        if status.upper() != AUTHORITATIVE_STATUS:
            errors.append(
                f"Row {idx}: {code or '<missing code>'} status must be exactly "
                f"{AUTHORITATIVE_STATUS!r}; found {status!r}."
            )
        if not mapping_notes or is_placeholder(mapping_notes):
            errors.append(
                f"Row {idx}: {code or '<missing code>'} mapping_notes must record the owner mapping basis."
            )

        mapped_by_relative_path[file_name] = {
            "document_code": code,
            "file_name": file_name,
            "status": status,
            "mapping_notes": mapping_notes,
            "source_row": str(idx),
        }

    missing_codes = sorted(REQUIRED_CODE_SET - set(seen_codes))
    if missing_codes:
        errors.append("Missing required document codes: " + ", ".join(missing_codes) + ".")
    unmapped_files = sorted(set(corpus_relative_paths) - set(mapped_by_relative_path))
    if unmapped_files:
        errors.append(
            "Corpus contains original files absent from the local mapping manifest: "
            + ", ".join(unmapped_files)
            + "."
        )
    if not errors:
        warnings.append(
            "Original filenames are preserved; CRAVE document identity comes from the "
            "separate authoritative local mapping manifest."
        )
    return mapped_by_relative_path, errors, warnings


def validate_corpus_dir(path: Path, local_mapping_csv: Path | None = None) -> IntakeResult:
    errors: list[str] = []
    warnings: list[str] = []
    records: list[dict[str, Any]] = []

    if not path.exists():
        return IntakeResult(False, "corpus_dir", [f"Corpus folder not found: {path}"], [], [])
    if not path.is_dir():
        return IntakeResult(False, "corpus_dir", [f"Corpus path is not a folder: {path}"], [], [])

    files = sorted(item for item in path.rglob("*") if item.is_file() and not item.name.startswith("."))
    local_mapping: dict[str, dict[str, str]] = {}
    mode = "corpus_dir_filename_code_fallback"
    if local_mapping_csv is not None:
        mode = "corpus_dir_original_filename_mapping"
        local_mapping, mapping_errors, mapping_warnings = load_local_filename_mapping(
            local_mapping_csv,
            path,
            files,
        )
        errors.extend(mapping_errors)
        warnings.extend(mapping_warnings)
    matched_by_code: dict[str, list[Path]] = {code: [] for code in REQUIRED_CODES}
    unmatched_files: list[str] = []
    hash_owners: dict[str, str] = {}

    for file_path in files:
        relative_path = str(file_path.relative_to(path))
        mapping_record = local_mapping.get(relative_path) if local_mapping_csv is not None else None
        matches = (
            [mapping_record["document_code"]]
            if mapping_record and mapping_record.get("document_code") in REQUIRED_CODE_SET
            else []
            if local_mapping_csv is not None
            else code_matches_for_file(file_path)
        )
        suffix = file_path.suffix.lower()
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

        if not matches:
            unmatched_files.append(str(file_path.relative_to(path)))
            continue
        if len(matches) > 1:
            errors.append(
                f"{file_path.relative_to(path)} matches multiple required codes: "
                + ", ".join(matches)
                + "."
            )
            continue

        code = matches[0]
        matched_by_code[code].append(file_path)

        if suffix in ARCHIVE_EXTENSIONS or looks_like_archive(file_path.name, mime_type):
            errors.append(f"{code}: archive-like source file is not accepted: {file_path.name}.")
        if suffix in REJECTED_EXTENSIONS:
            errors.append(f"{code}: non-source text/metadata file is not accepted: {file_path.name}.")
        if suffix not in ALLOWED_SOURCE_EXTENSIONS:
            errors.append(
                f"{code}: unsupported source extension {suffix or '<none>'}; "
                "expected .pdf."
            )

        try:
            with file_path.open("rb") as handle:
                pdf_signature = handle.read(5)
        except OSError as exc:
            errors.append(f"{code}: cannot read source file {file_path.name}: {exc}.")
            continue
        if pdf_signature != b"%PDF-":
            errors.append(f"{code}: file does not have a PDF signature: {file_path.name}.")

        draft_marker = contains_forbidden_authoritative_marker(file_path)
        if draft_marker:
            errors.append(
                f"{code}: controlled draft marker {draft_marker!r} is not accepted "
                "as authoritative corpus evidence."
            )

        digest = sha256_file(file_path)
        prior_code = hash_owners.get(digest)
        if prior_code and prior_code != code:
            errors.append(
                f"{code}: binary SHA-256 is identical to {prior_code}; "
                "renamed duplicate files cannot represent two authoritative documents."
            )
        else:
            hash_owners[digest] = code

        records.append(
            {
                "document_code": code,
                "relative_path": relative_path,
                "original_file_name": file_path.name,
                "identity_binding": (
                    "authoritative_local_mapping_manifest"
                    if local_mapping_csv is not None
                    else "legacy_filename_code_fallback"
                ),
                "mapping_status": mapping_record.get("status") if mapping_record else None,
                "mapping_notes": mapping_record.get("mapping_notes") if mapping_record else None,
                "size_bytes": file_path.stat().st_size,
                "sha256": digest,
                "mime_type": mime_type,
            }
        )

    for code, matched_files in matched_by_code.items():
        if not matched_files:
            errors.append(f"Missing required source file for {code}.")
        elif len(matched_files) > 1:
            relative_names = ", ".join(str(item.relative_to(path)) for item in matched_files)
            errors.append(f"{code}: expected exactly one source file, found {len(matched_files)}: {relative_names}.")

    if unmatched_files:
        if local_mapping_csv is not None:
            errors.append(
                "Corpus folder contains files not bound by the local mapping manifest: "
                + ", ".join(unmatched_files)
                + "."
            )
        else:
            errors.append(
                "Corpus folder contains files that do not match any required document code: "
                + ", ".join(unmatched_files)
                + "."
            )

    if len(records) != len(REQUIRED_CODES):
        errors.append(f"Corpus folder must produce exactly 12 source records; found {len(records)}.")

    if not errors:
        warnings.append(
            "Corrected corpus folder validates with original filename and SHA-256 lineage; bounded parse "
            "evidence and human reviewer decisions are still required before BLK-004 closure."
        )

    return IntakeResult(not errors, mode, errors, warnings, sorted(records, key=lambda r: r["document_code"]))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mapping-csv", type=Path, help="CSV containing document_code to Drive file ID mapping.")
    mode.add_argument("--corpus-dir", type=Path, help="Corrected local corpus folder with one source file per code.")
    parser.add_argument(
        "--local-mapping-csv",
        type=Path,
        help="Optional document_code to original corpus filename manifest; valid only with --corpus-dir.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.mapping_csv:
        if args.local_mapping_csv:
            raise SystemExit("--local-mapping-csv is valid only with --corpus-dir.")
        result = validate_mapping_csv(args.mapping_csv)
    else:
        result = validate_corpus_dir(args.corpus_dir, args.local_mapping_csv)

    report = result.as_report()
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")

    print(serialized)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
