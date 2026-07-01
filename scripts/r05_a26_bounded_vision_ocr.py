#!/usr/bin/env python3
"""Run bounded local Apple Vision OCR evidence for R05-A26 BLK-004.

The operator renders only explicitly selected PDF pages, runs three local Vision
passes, stores hashes/counts/confidence plus a short review preview, and deletes
temporary images. It never auto-approves OCR output or touches remote systems.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "work/r05_authoritative_corpus/PDA TR 39 (2).pdf"
DEFAULT_A25_REPORT = ROOT / "work/r05_a25_actual_filename_parse_evidence_report.json"
DEFAULT_OUTPUT = ROOT / "work/r05_a26_bounded_vision_ocr_report.json"
DEFAULT_CORPUS_REVIEW_QUEUE = ROOT / "work/r05_a26_blk004_corpus_review_queue.csv"
DEFAULT_OCR_REVIEW_QUEUE = ROOT / "work/r05_a26_ocr_page_review_queue.csv"
VISION_SOURCE = ROOT / "scripts/r05_a26_macos_vision_ocr.m"
DEFAULT_PAGES = (1, 2, 3, 9, 17)
PASS_SPECS = (
    {"pass_id": "vision_accurate_300", "dpi": 300, "mode": "accurate"},
    {"pass_id": "vision_accurate_400", "dpi": 400, "mode": "accurate"},
    {"pass_id": "vision_fast_150", "dpi": 150, "mode": "fast"},
)
MIN_TEXT_WORDS = 8
MIN_SIMILARITY = 0.95
MAX_WORD_DELTA_RATIO = 0.05
MIN_MEAN_CONFIDENCE = 0.85
CRITICAL_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:No\.\s*[A-Za-z0-9-]+|\d+(?:[.,]\d+)?"
    r"(?:\s*(?:%|°\s*C|mg|µg|ug|mL|L|bar|psi|Pa|kPa|MPa|CFU|mm|cm|m)"
    r"(?![A-Za-z]))?)(?![A-Za-z])",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def normalize_ocr_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return " ".join(normalized.split())


def critical_tokens(value: str) -> list[str]:
    return sorted({" ".join(match.group(0).lower().split()) for match in CRITICAL_TOKEN_PATTERN.finditer(value)})


def compare_passes(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_text = str(left.get("normalized_text") or "")
    right_text = str(right.get("normalized_text") or "")
    similarity = SequenceMatcher(None, left_text, right_text, autojunk=False).ratio()
    left_words = int(left.get("word_count") or 0)
    right_words = int(right.get("word_count") or 0)
    word_delta_ratio = abs(left_words - right_words) / max(left_words, right_words, 1)
    left_tokens = set(left.get("critical_tokens") or [])
    right_tokens = set(right.get("critical_tokens") or [])
    tokens_match = left_tokens == right_tokens
    return {
        "left_pass": left["pass_id"],
        "right_pass": right["pass_id"],
        "text_similarity": round(similarity, 6),
        "word_delta_ratio": round(word_delta_ratio, 6),
        "critical_tokens_match": tokens_match,
        "critical_tokens_only_left": sorted(left_tokens - right_tokens),
        "critical_tokens_only_right": sorted(right_tokens - left_tokens),
        "agreement_pass": (
            similarity >= MIN_SIMILARITY
            and word_delta_ratio <= MAX_WORD_DELTA_RATIO
            and tokens_match
        ),
    }


def compile_vision_tool(output_path: Path) -> dict[str, Any]:
    clang = shutil.which("clang")
    if not clang:
        raise RuntimeError("clang is unavailable; cannot compile local Vision OCR helper.")
    command = [
        clang,
        "-fobjc-arc",
        "-framework",
        "Foundation",
        "-framework",
        "Vision",
        "-framework",
        "ImageIO",
        "-framework",
        "CoreGraphics",
        str(VISION_SOURCE),
        "-o",
        str(output_path),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Vision helper compile failed: {completed.stderr.strip()}")
    return {
        "compiler": clang,
        "source_sha256": sha256_file(VISION_SOURCE),
        "binary_sha256": sha256_file(output_path),
    }


def render_page(pdf_path: Path, page_number: int, dpi: int, output_prefix: Path) -> Path:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is unavailable.")
    command = [
        pdftoppm,
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        "-r",
        str(dpi),
        "-png",
        "-singlefile",
        str(pdf_path),
        str(output_prefix),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    image_path = output_prefix.with_suffix(".png")
    if completed.returncode != 0 or not image_path.exists():
        raise RuntimeError(
            f"Page {page_number} render failed at {dpi} DPI: {completed.stderr.strip()}"
        )
    return image_path


def run_vision_pass(
    executable: Path,
    image_path: Path,
    pass_spec: dict[str, Any],
    languages: str,
) -> dict[str, Any]:
    command = [str(executable), str(image_path), str(pass_spec["mode"]), languages]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{pass_spec['pass_id']} failed: {(completed.stderr or completed.stdout).strip()}"
        )
    payload = json.loads(completed.stdout)
    text = str(payload.pop("text", ""))
    lines = payload.pop("lines", [])
    normalized = normalize_ocr_text(text)
    low_confidence_lines = sum(
        1 for line in lines if float(line.get("confidence") or 0.0) < MIN_MEAN_CONFIDENCE
    )
    return {
        "pass_id": pass_spec["pass_id"],
        "engine": payload.get("engine"),
        "mode": payload.get("mode"),
        "dpi": pass_spec["dpi"],
        "languages": payload.get("languages", []),
        "rendered_image_sha256": sha256_file(image_path),
        "line_count": int(payload.get("line_count") or 0),
        "char_count": int(payload.get("char_count") or 0),
        "word_count": int(payload.get("word_count") or 0),
        "mean_confidence": round(float(payload.get("mean_confidence") or 0.0), 6),
        "minimum_confidence": round(float(payload.get("minimum_confidence") or 0.0), 6),
        "low_confidence_line_count": low_confidence_lines,
        "text_sha256": sha256_text(text),
        "normalized_text_sha256": sha256_text(normalized),
        "normalized_text": normalized,
        "critical_tokens": critical_tokens(text),
        "review_preview": " ".join(text.split())[:240],
        "full_text_retained": False,
        "line_payload_retained": False,
    }


def expected_sha256_from_a25(a25_report: Path, file_name: str) -> str | None:
    if not a25_report.exists():
        return None
    try:
        payload = json.loads(a25_report.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for record in payload.get("records", []):
        if record.get("file_name") == file_name:
            digest = record.get("sha256")
            return digest if isinstance(digest, str) else None
    return None


def a25_corpus_context(a25_report: Path) -> dict[str, Any]:
    if not a25_report.exists():
        return {}
    try:
        payload = json.loads(a25_report.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    summary = payload.get("summary") or {}
    return {
        "pdf_file_count": int(summary.get("pdf_file_count") or 0),
        "text_layer_parse_ready_records": int(summary.get("parse_ready_records") or 0),
        "parse_or_ocr_review_required_records": int(
            summary.get("parse_review_required_records") or 0
        ),
        "mapping_complete": bool(summary.get("mapping_complete")),
        "mapped_records": int(summary.get("mapped_records") or 0),
    }


def page_count(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        raise RuntimeError(f"pypdf unavailable: {exc!r}") from exc
    return len(PdfReader(str(pdf_path)).pages)


def write_review_queues(
    report: dict[str, Any],
    a25_report_path: Path,
    corpus_queue_path: Path,
    ocr_queue_path: Path,
) -> None:
    a25_payload = json.loads(a25_report_path.read_text(encoding="utf-8"))
    corpus_fields = [
        "file_name",
        "source_sha256",
        "extraction_path",
        "sample_pages",
        "technical_evidence_status",
        "mapping_status",
        "table_or_figure_review_required",
        "reviewer_name",
        "reviewer_role",
        "review_status",
        "reviewed_at",
        "reviewer_decision",
        "reviewer_notes",
        "auto_approve",
    ]
    corpus_rows: list[dict[str, Any]] = []
    ocr_source_name = report["source"]["file_name"]
    for record in a25_payload.get("records", []):
        is_ocr_source = record.get("file_name") == ocr_source_name
        corpus_rows.append(
            {
                "file_name": record.get("file_name"),
                "source_sha256": record.get("sha256"),
                "extraction_path": (
                    "BOUNDED_APPLE_VISION_OCR"
                    if is_ocr_source
                    else "TEXT_LAYER_PYPDF_PDFPLUMBER"
                ),
                "sample_pages": ",".join(str(page) for page in record.get("sample_pages", [])),
                "technical_evidence_status": "TECHNICAL_EVIDENCE_RECORDED_REVIEW_REQUIRED",
                "mapping_status": record.get("mapping_status"),
                "table_or_figure_review_required": str(
                    bool(record.get("requires_table_or_figure_review"))
                ).upper(),
                "reviewer_name": "",
                "reviewer_role": "",
                "review_status": "PENDING_ACCOUNTABLE_HUMAN_REVIEW",
                "reviewed_at": "",
                "reviewer_decision": "PENDING",
                "reviewer_notes": "",
                "auto_approve": "FALSE",
            }
        )
    corpus_queue_path.parent.mkdir(parents=True, exist_ok=True)
    with corpus_queue_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=corpus_fields)
        writer.writeheader()
        writer.writerows(corpus_rows)

    ocr_fields = [
        "file_name",
        "source_sha256",
        "page_number",
        "ocr_decision",
        "accurate_pair_agreement_pass",
        "accurate_passes_meet_mean_confidence",
        "all_pairwise_agreements_pass",
        "reviewer_name",
        "reviewer_role",
        "review_status",
        "reviewed_at",
        "reviewer_decision",
        "reviewer_notes",
        "auto_approve",
    ]
    ocr_rows = [
        {
            "file_name": ocr_source_name,
            "source_sha256": report["source"]["sha256"],
            "page_number": page["page_number"],
            "ocr_decision": page["decision"],
            "accurate_pair_agreement_pass": str(page["accurate_pair_agreement_pass"]).upper(),
            "accurate_passes_meet_mean_confidence": str(
                page["accurate_passes_meet_mean_confidence"]
            ).upper(),
            "all_pairwise_agreements_pass": str(page["all_pairwise_agreements_pass"]).upper(),
            "reviewer_name": "",
            "reviewer_role": "",
            "review_status": "PENDING_ACCOUNTABLE_HUMAN_REVIEW",
            "reviewed_at": "",
            "reviewer_decision": "PENDING",
            "reviewer_notes": "",
            "auto_approve": "FALSE",
        }
        for page in report.get("pages", [])
    ]
    ocr_queue_path.parent.mkdir(parents=True, exist_ok=True)
    with ocr_queue_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ocr_fields)
        writer.writeheader()
        writer.writerows(ocr_rows)


def build_report(
    pdf_path: Path,
    pages: tuple[int, ...],
    languages: str,
    a25_report: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    page_records: list[dict[str, Any]] = []
    source_sha256 = sha256_file(pdf_path) if pdf_path.exists() else None
    expected_sha256 = expected_sha256_from_a25(a25_report, pdf_path.name)
    if not pdf_path.exists() or not pdf_path.is_file():
        errors.append(f"PDF not found: {pdf_path}")
    elif pdf_path.suffix.lower() != ".pdf":
        errors.append(f"Input must be a PDF: {pdf_path}")
    elif expected_sha256 and source_sha256 != expected_sha256:
        errors.append("Source SHA-256 does not match retained A25 evidence.")

    total_pages = page_count(pdf_path) if not errors else 0
    if not pages or len(pages) > 8:
        errors.append("Bounded OCR requires between 1 and 8 selected pages.")
    invalid_pages = [page for page in pages if page < 1 or page > total_pages]
    if invalid_pages:
        errors.append(f"Selected pages are outside PDF bounds: {invalid_pages}")

    compiler_evidence: dict[str, Any] = {}
    if not errors:
        with tempfile.TemporaryDirectory(prefix="crave-r05-a26-") as temp_dir:
            temp_path = Path(temp_dir)
            executable = temp_path / "r05_a26_macos_vision_ocr"
            try:
                compiler_evidence = compile_vision_tool(executable)
                for page in pages:
                    passes: list[dict[str, Any]] = []
                    for pass_spec in PASS_SPECS:
                        prefix = temp_path / f"page-{page}-{pass_spec['dpi']}"
                        image_path = render_page(pdf_path, page, int(pass_spec["dpi"]), prefix)
                        result = run_vision_pass(executable, image_path, pass_spec, languages)
                        passes.append(result)
                    comparisons = [
                        compare_passes(passes[left], passes[right])
                        for left in range(len(passes))
                        for right in range(left + 1, len(passes))
                    ]
                    all_have_text = all(result["word_count"] >= MIN_TEXT_WORDS for result in passes)
                    accurate_confidence_ready = all(
                        result["mean_confidence"] >= MIN_MEAN_CONFIDENCE for result in passes[:2]
                    )
                    all_passes_confidence_ready = all(
                        result["mean_confidence"] >= MIN_MEAN_CONFIDENCE for result in passes
                    )
                    accurate_pair_agreement = comparisons[0]["agreement_pass"]
                    all_pairwise_agreement = all(item["agreement_pass"] for item in comparisons)
                    if not all_have_text:
                        page_decision = "OCR_INSUFFICIENT_TEXT_REVIEW_REQUIRED"
                    elif not accurate_pair_agreement:
                        page_decision = "OCR_ACCURATE_PASS_DISAGREEMENT_REVIEW_REQUIRED"
                    elif not accurate_confidence_ready:
                        page_decision = "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED"
                    elif all_pairwise_agreement and all_passes_confidence_ready:
                        page_decision = "OCR_REVIEW_CANDIDATE"
                    else:
                        page_decision = "OCR_REVIEW_CANDIDATE_FAST_PASS_VARIANCE"
                    page_records.append(
                        {
                            "page_number": page,
                            "passes": [
                                {key: value for key, value in result.items() if key != "normalized_text"}
                                for result in passes
                            ],
                            "comparisons": comparisons,
                            "all_passes_have_minimum_text": all_have_text,
                            "accurate_passes_meet_mean_confidence": accurate_confidence_ready,
                            "all_passes_meet_mean_confidence": all_passes_confidence_ready,
                            "accurate_pair_agreement_pass": accurate_pair_agreement,
                            "all_pairwise_agreements_pass": all_pairwise_agreement,
                            "decision": page_decision,
                            "auto_approve": False,
                        }
                    )
            except (OSError, RuntimeError, json.JSONDecodeError) as exc:
                errors.append(str(exc))

    execution_ok = not errors and len(page_records) == len(pages)
    review_required = True
    a25_context = a25_corpus_context(a25_report)
    bounded_ocr_covered_records = 1 if execution_ok and expected_sha256 else 0
    technical_extraction_covered_records = min(
        a25_context.get("pdf_file_count", 0),
        a25_context.get("text_layer_parse_ready_records", 0) + bounded_ocr_covered_records,
    )
    technical_extraction_complete = bool(
        a25_context.get("pdf_file_count")
        and technical_extraction_covered_records == a25_context["pdf_file_count"]
    )
    return {
        "schema_version": 1,
        "rhythm": "R05-A26",
        "gate": "P0_BLK004_BOUNDED_LOCAL_OCR_EVIDENCE",
        "execution_ok": execution_ok,
        "decision": (
            "BOUNDED_OCR_EVIDENCE_RECORDED_HUMAN_REVIEW_REQUIRED"
            if execution_ok
            else "FAIL_CLOSED_BOUNDED_OCR_EXECUTION_ERROR"
        ),
        "errors": errors,
        "source": {
            "file_name": pdf_path.name,
            "path": str(pdf_path),
            "sha256": source_sha256,
            "expected_a25_sha256": expected_sha256,
            "sha256_matches_a25": bool(expected_sha256 and source_sha256 == expected_sha256),
            "page_count": total_pages,
        },
        "bounded_scope": {
            "selected_pages": list(pages),
            "selected_page_count": len(pages),
            "full_document_ocr": False,
            "pass_specs": list(PASS_SPECS),
            "languages": [value for value in languages.split(",") if value],
        },
        "compiler_evidence": compiler_evidence,
        "pages": page_records,
        "corpus_evidence_summary": {
            **a25_context,
            "bounded_ocr_evidence_records": bounded_ocr_covered_records,
            "technical_extraction_covered_records": technical_extraction_covered_records,
            "technical_extraction_evidence_complete": technical_extraction_complete,
            "technical_extraction_is_not_human_approval": True,
        },
        "summary": {
            "page_records": len(page_records),
            "passes_executed": sum(len(record["passes"]) for record in page_records),
            "review_candidate_pages": sum(
                1 for record in page_records if record["decision"] == "OCR_REVIEW_CANDIDATE"
            ),
            "review_candidate_fast_variance_pages": sum(
                1
                for record in page_records
                if record["decision"] == "OCR_REVIEW_CANDIDATE_FAST_PASS_VARIANCE"
            ),
            "accurate_pass_disagreement_pages": sum(
                1
                for record in page_records
                if record["decision"] == "OCR_ACCURATE_PASS_DISAGREEMENT_REVIEW_REQUIRED"
            ),
            "low_confidence_pages": sum(
                1
                for record in page_records
                if record["decision"] == "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED"
            ),
            "insufficient_text_pages": sum(
                1
                for record in page_records
                if record["decision"] == "OCR_INSUFFICIENT_TEXT_REVIEW_REQUIRED"
            ),
            "human_review_required": review_required,
            "auto_approved_pages": 0,
        },
        "quality_controls": {
            "original_filename_preserved": True,
            "source_sha256_locked_to_a25": bool(expected_sha256),
            "bounded_pages_only": True,
            "multi_pass_single_engine": True,
            "independent_multi_engine_claimed": False,
            "full_ocr_performed": False,
            "full_ocr_text_retained": False,
            "human_review_required": True,
            "auto_approval": False,
            "supabase_write": False,
            "n8n_operation": False,
            "git_remote": False,
        },
        "blockers": {
            "BLK-003": "OPEN_SEPARATE_IDENTITY_MAPPING_REQUIRED",
            "BLK-004": (
                "OPEN_TECHNICAL_EXTRACTION_COVERED_MAPPING_AND_HUMAN_REVIEW_REQUIRED"
                if technical_extraction_complete
                else "OPEN_BOUNDED_OCR_EVIDENCE_INCOMPLETE"
            ),
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }


def parse_pages(raw: str) -> tuple[int, ...]:
    try:
        pages = tuple(dict.fromkeys(int(value.strip()) for value in raw.split(",") if value.strip()))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Pages must be comma-separated integers.") from exc
    return pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--pages", type=parse_pages, default=DEFAULT_PAGES)
    parser.add_argument("--languages", default="en-US")
    parser.add_argument("--a25-report", type=Path, default=DEFAULT_A25_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--corpus-review-queue", type=Path, default=DEFAULT_CORPUS_REVIEW_QUEUE)
    parser.add_argument("--ocr-review-queue", type=Path, default=DEFAULT_OCR_REVIEW_QUEUE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.pdf, args.pages, args.languages, args.a25_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if report["execution_ok"]:
        write_review_queues(
            report,
            args.a25_report,
            args.corpus_review_queue,
            args.ocr_review_queue,
        )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "execution_ok": report["execution_ok"],
                "source": report["source"],
                "summary": report["summary"],
                "remote_operations": report["remote_operations"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["execution_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
