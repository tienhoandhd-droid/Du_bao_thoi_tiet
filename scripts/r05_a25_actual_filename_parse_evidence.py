#!/usr/bin/env python3
"""Build bounded parse evidence for an actual-filename R05 corpus.

R05-A25 is local-only. It accepts a folder where the source PDFs keep their real
file names instead of CRAVE document-code names. It computes byte/hash/page/text
layer evidence and writes a mapping template, but it does not approve mappings,
write Supabase, execute n8n, OCR full documents, chunk/embed, or touch Git remote.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from r05_authoritative_corpus_intake import (
    AUTHORITATIVE_STATUS,
    REQUIRED_CODES,
    REQUIRED_CODE_SET,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"
DEFAULT_OUTPUT = ROOT / "work/r05_a25_actual_filename_parse_evidence_report.json"
DEFAULT_MAPPING_TEMPLATE = ROOT / "work/r05_a25_actual_filename_mapping_required.csv"

PDF_MIME_TYPE = "application/pdf"
MIN_TEXT_WORDS = 80
MAX_SAMPLE_PAGES = 5
MAPPING_STATUSES = {
    AUTHORITATIVE_STATUS,
    "OWNER_CONFIRMED_FILENAME_MAPPING",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def text_stats(text: str) -> dict[str, Any]:
    return {
        "chars": len(text),
        "words": len(re.findall(r"\w+", text, flags=re.UNICODE)),
        "non_whitespace_chars": sum(1 for char in text if not char.isspace()),
        "sha256": sha256_text(text),
    }


def sample_page_numbers(page_count: int, max_pages: int = MAX_SAMPLE_PAGES) -> list[int]:
    if page_count <= 0:
        return []
    candidates = [1, 2, 3, page_count]
    if page_count > 6:
        candidates.append((page_count + 1) // 2)
    return sorted({page for page in candidates if 1 <= page <= page_count})[:max_pages]


def pypdf_evidence(path: Path, pages: list[int]) -> dict[str, Any]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        return {"available": False, "error": f"pypdf_unavailable:{exc!r}"}

    try:
        reader = PdfReader(str(path))
        metadata = {
            str(key): str(value)
            for key, value in (reader.metadata or {}).items()
            if value is not None
        }
        chunks: list[str] = []
        page_errors: list[str] = []
        for page_number in pages:
            try:
                chunks.append(reader.pages[page_number - 1].extract_text() or "")
            except Exception as exc:  # pragma: no cover - defensive parser boundary
                page_errors.append(f"page {page_number}: {exc!r}")
        combined = "\n".join(chunks)
        return {
            "available": True,
            "page_count": len(reader.pages),
            "encrypted": bool(reader.is_encrypted),
            "metadata_title": metadata.get("/Title"),
            "metadata_author": metadata.get("/Author"),
            "metadata_producer": metadata.get("/Producer"),
            "sample_text": text_stats(combined),
            "page_errors": page_errors,
        }
    except Exception as exc:  # pragma: no cover - defensive parser boundary
        return {"available": True, "error": repr(exc)}


def pdfplumber_evidence(path: Path, pages: list[int]) -> dict[str, Any]:
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        return {"available": False, "error": f"pdfplumber_unavailable:{exc!r}"}

    try:
        page_records: list[dict[str, Any]] = []
        chunks: list[str] = []
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page_number in pages:
                page = pdf.pages[page_number - 1]
                text = page.extract_text() or ""
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
                tables = page.find_tables()
                chunks.append(text)
                page_records.append(
                    {
                        "page_number": page_number,
                        "text_chars": len(text),
                        "word_count": len(words),
                        "table_count": len(tables),
                        "image_count": len(page.images),
                        "rect_count": len(page.rects),
                        "curve_count": len(page.curves),
                    }
                )
        combined = "\n".join(chunks)
        return {
            "available": True,
            "page_count": page_count,
            "sample_text": text_stats(combined),
            "sample_pages": page_records,
            "table_count": sum(page["table_count"] for page in page_records),
            "image_count": sum(page["image_count"] for page in page_records),
            "shape_count": sum(page["rect_count"] + page["curve_count"] for page in page_records),
        }
    except Exception as exc:  # pragma: no cover - defensive parser boundary
        return {"available": True, "error": repr(exc)}


@dataclass(frozen=True)
class MappingValidation:
    complete: bool
    records_by_file: dict[str, dict[str, str]]
    errors: list[str]
    warnings: list[str]


def load_mapping(path: Path | None, corpus_files: list[Path]) -> MappingValidation:
    if path is None or not path.exists():
        return MappingValidation(
            complete=False,
            records_by_file={},
            errors=[],
            warnings=["No actual-filename mapping CSV was provided."],
        )

    rows: list[dict[str, str]]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    required_columns = {"document_code", "file_name", "status"}
    fieldnames = set(rows[0].keys()) if rows else set()
    errors: list[str] = []
    warnings: list[str] = []
    if not rows:
        errors.append("Actual-filename mapping CSV is empty.")
    missing_columns = sorted(required_columns - fieldnames)
    if missing_columns:
        errors.append("Actual-filename mapping CSV is missing columns: " + ", ".join(missing_columns) + ".")

    existing_names = {path.name for path in corpus_files}
    seen_codes: dict[str, str] = {}
    seen_files: dict[str, str] = {}
    records_by_file: dict[str, dict[str, str]] = {}

    for row_number, row in enumerate(rows, start=2):
        code = (row.get("document_code") or "").strip()
        file_name = (row.get("file_name") or "").strip()
        status = (row.get("status") or "").strip()
        notes = (row.get("mapping_notes") or "").strip()
        record = {
            "document_code": code,
            "file_name": file_name,
            "status": status,
            "mapping_notes": notes,
        }

        if code not in REQUIRED_CODE_SET:
            errors.append(f"Row {row_number}: unexpected or missing document_code {code!r}.")
        elif code in seen_codes:
            errors.append(f"Row {row_number}: duplicate document_code {code}; first file {seen_codes[code]!r}.")
        else:
            seen_codes[code] = file_name

        if file_name not in existing_names:
            errors.append(f"Row {row_number}: mapped file is not present in corpus folder: {file_name!r}.")
        elif file_name in seen_files:
            errors.append(f"Row {row_number}: duplicate file_name {file_name!r}; first code {seen_files[file_name]}.")
        else:
            seen_files[file_name] = code
            records_by_file[file_name] = record

        if status.upper() not in MAPPING_STATUSES:
            errors.append(
                f"Row {row_number}: status for {code or file_name} must be one of "
                + ", ".join(sorted(MAPPING_STATUSES))
                + f"; found {status!r}."
            )

    missing_codes = sorted(REQUIRED_CODE_SET - set(seen_codes))
    missing_files = sorted(existing_names - set(seen_files))
    if missing_codes:
        errors.append("Missing required document codes in mapping: " + ", ".join(missing_codes) + ".")
    if missing_files:
        errors.append("Corpus files not mapped to any document code: " + ", ".join(missing_files) + ".")
    if len(rows) != len(REQUIRED_CODES):
        errors.append(f"Actual-filename mapping CSV must contain exactly 12 rows; found {len(rows)}.")

    if not errors:
        warnings.append("Actual filename mapping is complete, but reviewer approval is still required before BLK-004 closure.")
    return MappingValidation(not errors, records_by_file, errors, warnings)


def write_mapping_template(path: Path, corpus_files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "document_code",
        "file_name",
        "status",
        "mapping_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for file_path in sorted(corpus_files, key=lambda item: item.name.lower()):
            writer.writerow(
                {
                    "document_code": "REQUIRED_OWNER_MAPPING",
                    "file_name": file_path.name,
                    "status": "PENDING_OWNER_CONFIRMATION",
                    "mapping_notes": "Fill exact CRAVE document_code; do not rely on row order.",
                }
            )


def build_report(corpus_dir: Path, mapping_csv: Path | None, mapping_template: Path | None) -> dict[str, Any]:
    if not corpus_dir.exists() or not corpus_dir.is_dir():
        return {
            "schema_version": 1,
            "rhythm": "R05-A25",
            "gate": "P0_BLK004_ACTUAL_FILENAME_PARSE_EVIDENCE",
            "ok": False,
            "decision": "FAIL_CLOSED_CORPUS_FOLDER_REQUIRED",
            "errors": [f"Corpus folder not found or not a directory: {corpus_dir}"],
            "records": [],
            "remote_operations": {"supabase": [], "n8n": [], "git": []},
        }

    corpus_files = sorted(
        path for path in corpus_dir.iterdir() if path.is_file() and not path.name.startswith(".")
    )
    pdf_files = [path for path in corpus_files if path.suffix.lower() == ".pdf"]
    errors: list[str] = []
    warnings: list[str] = []
    if len(corpus_files) != len(pdf_files):
        errors.append("Corpus folder contains non-PDF source files.")
    if len(pdf_files) != len(REQUIRED_CODES):
        errors.append(f"Actual-filename corpus must contain exactly 12 PDFs; found {len(pdf_files)}.")

    mapping = load_mapping(mapping_csv, pdf_files)
    if mapping_template is not None:
        write_mapping_template(mapping_template, pdf_files)

    hash_owners: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    for path in pdf_files:
        size_bytes = path.stat().st_size
        digest = sha256_file(path)
        prior_name = hash_owners.get(digest)
        if prior_name and prior_name != path.name:
            errors.append(f"{path.name}: duplicate SHA-256 with {prior_name}.")
        hash_owners[digest] = path.name

        with path.open("rb") as handle:
            is_pdf = handle.read(5) == b"%PDF-"
        if not is_pdf:
            errors.append(f"{path.name}: missing PDF signature.")

        # Read page count first with pypdf so sampling stays bounded.
        initial = pypdf_evidence(path, [])
        page_count = int(initial.get("page_count") or 0)
        pages = sample_page_numbers(page_count)
        pypdf = pypdf_evidence(path, pages)
        pdfplumber = pdfplumber_evidence(path, pages)
        pypdf_words = ((pypdf.get("sample_text") or {}).get("words") or 0) if pypdf.get("available") else 0
        plumber_words = ((pdfplumber.get("sample_text") or {}).get("words") or 0) if pdfplumber.get("available") else 0
        parser_errors = [
            value.get("error")
            for value in (pypdf, pdfplumber)
            if isinstance(value, dict) and value.get("error")
        ]
        table_count = int(pdfplumber.get("table_count") or 0) if pdfplumber.get("available") else 0
        image_count = int(pdfplumber.get("image_count") or 0) if pdfplumber.get("available") else 0
        shape_count = int(pdfplumber.get("shape_count") or 0) if pdfplumber.get("available") else 0
        max_words = max(pypdf_words, plumber_words)
        parse_status = (
            "PARSE_ERROR_REVIEW_REQUIRED"
            if parser_errors
            else "TEXT_LAYER_PARSE_EVIDENCE_READY"
            if max_words >= MIN_TEXT_WORDS
            else "LOW_TEXT_LAYER_REVIEW_OR_OCR_REQUIRED"
        )
        mapping_record = mapping.records_by_file.get(path.name)
        records.append(
            {
                "file_name": path.name,
                "mapped_document_code": mapping_record.get("document_code") if mapping_record else None,
                "mapping_status": mapping_record.get("status") if mapping_record else "PENDING_OWNER_MAPPING",
                "size_bytes": size_bytes,
                "sha256": digest,
                "mime_type": PDF_MIME_TYPE,
                "pdf_signature": is_pdf,
                "page_count": page_count,
                "sample_pages": pages,
                "pypdf": pypdf,
                "pdfplumber": pdfplumber,
                "table_count_on_sampled_pages": table_count,
                "image_count_on_sampled_pages": image_count,
                "shape_count_on_sampled_pages": shape_count,
                "parse_status": parse_status,
                "requires_table_or_figure_review": table_count > 0 or image_count > 0 or shape_count > 30,
            }
        )

    parse_ready_count = sum(1 for record in records if record["parse_status"] == "TEXT_LAYER_PARSE_EVIDENCE_READY")
    parse_review_count = len(records) - parse_ready_count
    table_or_figure_review_count = sum(1 for record in records if record["requires_table_or_figure_review"])

    if mapping.errors:
        warnings.extend(mapping.errors)
    warnings.extend(mapping.warnings)
    if parse_review_count:
        errors.append(f"{parse_review_count} file(s) require parse/OCR review before BLK-004 closure.")

    ok = not errors and len(records) == len(REQUIRED_CODES)
    if parse_ready_count == len(REQUIRED_CODES) and not mapping.complete:
        decision = "LOCAL_PARSE_EVIDENCE_READY_MAPPING_REQUIRED"
    elif ok and mapping.complete:
        decision = "LOCAL_PARSE_EVIDENCE_READY_REVIEW_REQUIRED"
    elif parse_review_count:
        decision = "FAIL_CLOSED_PARSE_REVIEW_REQUIRED"
    else:
        decision = "FAIL_CLOSED_MAPPING_OR_CORPUS_REQUIRED"

    return {
        "schema_version": 1,
        "rhythm": "R05-A25",
        "gate": "P0_BLK004_ACTUAL_FILENAME_PARSE_EVIDENCE",
        "ok": ok and mapping.complete,
        "decision": decision,
        "corpus_dir": str(corpus_dir),
        "mapping_csv": str(mapping_csv) if mapping_csv else None,
        "mapping_template": str(mapping_template) if mapping_template else None,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "required_record_count": len(REQUIRED_CODES),
            "pdf_file_count": len(pdf_files),
            "parse_ready_records": parse_ready_count,
            "parse_review_required_records": parse_review_count,
            "table_or_figure_review_records": table_or_figure_review_count,
            "mapping_complete": mapping.complete,
            "mapped_records": sum(1 for record in records if record["mapped_document_code"]),
        },
        "records": records,
        "quality_controls": {
            "actual_filename_preserved": True,
            "row_order_mapping_denied": True,
            "bounded_sample_pages_only": True,
            "full_ocr_performed": False,
            "chunk_embed_performed": False,
            "supabase_write": False,
            "n8n_operation": False,
            "git_remote": False,
        },
        "blockers": {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN_PARSE_EVIDENCE_RECORDED_NOT_CLOSED",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "next_step": (
            "Fill the actual-filename mapping template with owner-confirmed CRAVE document codes, "
            "then run reviewer approval and controlled lineage linkage before BLK-004 closure."
        ),
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--mapping-csv", type=Path)
    parser.add_argument(
        "--mapping-template",
        type=Path,
        help=(
            "Optional mapping template output. Defaults to the retained template "
            "only when --corpus-dir is the repository default authoritative corpus."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping_template = args.mapping_template
    if mapping_template is None and args.corpus_dir.resolve() == DEFAULT_CORPUS.resolve():
        mapping_template = DEFAULT_MAPPING_TEMPLATE
    report = build_report(args.corpus_dir, args.mapping_csv, mapping_template)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "ok": report["ok"],
        "pdf_file_count": report.get("summary", {}).get("pdf_file_count"),
        "parse_ready_records": report.get("summary", {}).get("parse_ready_records"),
        "parse_review_required_records": report.get("summary", {}).get("parse_review_required_records"),
        "mapping_complete": report.get("summary", {}).get("mapping_complete"),
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
