#!/usr/bin/env python3
"""R05 raw-file hash and parse-quality probe.

Script này chỉ đọc file local và in JSON evidence. Nó không ghi Supabase, không
gọi n8n, không lưu binary vào DB. Dùng trước live gate để chứng minh:

- file có tồn tại thật;
- SHA-256 ổn định;
- PDF có header hợp lệ;
- parse text sample đủ dữ liệu tối thiểu nếu môi trường có pdfplumber.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def optional_pdfplumber() -> Any | None:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return None
    return pdfplumber


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_file(path: Path, sample_pages: int = 5) -> dict[str, Any]:
    data_prefix = path.read_bytes()[:8]
    header = data_prefix.decode("latin1", "replace")
    record: dict[str, Any] = {
        "path": str(path),
        "file_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "header": header,
        "is_pdf": header.startswith("%PDF-"),
    }

    if not record["is_pdf"]:
        record["parse_quality_status"] = "not_pdf_fail_closed"
        return record

    pdfplumber = optional_pdfplumber()
    if pdfplumber is None:
        record["parse_quality_status"] = "needs_review_no_pdfplumber"
        return record

    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            pages = pdf.pages[: min(sample_pages, page_count)]
            text = "\n".join((page.extract_text() or "") for page in pages)
    except Exception as error:  # pragma: no cover - defensive around PDF parser internals
        record["parse_quality_status"] = "parse_error"
        record["parse_error"] = repr(error)
        return record

    words = len(re.findall(r"\w+", text))
    non_whitespace = sum(1 for char in text if not char.isspace())
    record.update(
        {
            "parse_engine": "pdfplumber",
            "page_count": page_count,
            "sample_pages": len(pages),
            "sample_chars": len(text),
            "sample_words": words,
            "non_whitespace_chars": non_whitespace,
            "parse_quality_status": "pass_local_sample"
            if page_count >= 1 and words >= 80 and non_whitespace >= 500
            else "needs_review",
        }
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="File paths to probe")
    parser.add_argument("--sample-pages", type=int, default=5)
    args = parser.parse_args()

    records = [probe_file(Path(value), sample_pages=args.sample_pages) for value in args.paths]
    print(json.dumps({"records": records}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
