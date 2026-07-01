#!/usr/bin/env python3
"""Local-only R05-A08 page-7 table + figure benchmark.

This script intentionally writes only local evidence files. It does not import
data into Supabase and does not contact n8n.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import camelot
import cv2
import numpy as np
import pdfplumber
from PIL import Image
from pypdf import PdfReader, PdfWriter


def clean_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    return text


def normalize_matrix(matrix: list[list[Any]]) -> list[list[str]]:
    return [[clean_cell(cell) for cell in row] for row in matrix]


def matrix_shape(matrix: list[list[str]]) -> list[int]:
    return [len(matrix), max((len(row) for row in matrix), default=0)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def crop_and_hash(image: Image.Image, bbox_px: tuple[int, int, int, int], out_path: Path) -> dict:
    crop = image.crop(bbox_px)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path)
    return {
        "path": str(out_path),
        "bbox_px": list(map(int, bbox_px)),
        "width": crop.width,
        "height": crop.height,
        "sha256": sha256_file(out_path),
    }


def pdf_bbox_to_px(
    bbox: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    x0, top, x1, bottom = bbox
    sx = image_width / page_width
    sy = image_height / page_height
    return (
        max(0, int(round(x0 * sx))),
        max(0, int(round(top * sy))),
        min(image_width, int(round(x1 * sx))),
        min(image_height, int(round(bottom * sy))),
    )


def detect_figure_bbox(image_path: Path, table_bbox_px: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"Cannot read image: {image_path}")
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Dark ink only; this excludes most white background and keeps line art/text.
    mask = (gray < 210).astype("uint8") * 255
    # Exclude blue header, titles and the table region. The figure is the largest
    # connected dark-line object between title block and table top on page 7.
    mask[: int(height * 0.17), :] = 0
    mask[table_bbox_px[1] - 20 :, :] = 0
    mask[:, : int(width * 0.12)] = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (19, 19))
    dilated = cv2.dilate(mask, kernel, iterations=2)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dilated, 8)
    candidates = []
    for label in range(1, num_labels):
        x, y, w, h, area = stats[label]
        if area < 5000 or w < width * 0.15 or h < height * 0.10:
            continue
        if y > table_bbox_px[1]:
            continue
        candidates.append((area, x, y, w, h))
    if not candidates:
        raise RuntimeError("No figure candidate detected")
    _, x, y, w, h = max(candidates, key=lambda item: item[0])
    pad = 24
    return (
        max(0, int(x - pad)),
        max(0, int(y - pad)),
        min(width, int(x + w + pad)),
        min(height, int(y + h + pad)),
    )


def extract_native(pdf: Path, page_number: int) -> dict:
    with pdfplumber.open(pdf) as doc:
        page = doc.pages[page_number - 1]
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
        line_tables = page.find_tables()
        text_tables = page.find_tables(
            table_settings={
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 5,
            }
        )
        line_payload = []
        for table in line_tables:
            matrix = normalize_matrix(table.extract())
            line_payload.append({"bbox": list(table.bbox), "shape": matrix_shape(matrix), "matrix": matrix})
        text_payload = []
        for table in text_tables:
            matrix = normalize_matrix(table.extract())
            text_payload.append({"bbox": list(table.bbox), "shape": matrix_shape(matrix), "matrix": matrix})
    return {
        "engine": "pdfplumber/native",
        "page": page_number,
        "page_width": page.width,
        "page_height": page.height,
        "char_count": len(text),
        "word_count": len(words),
        "text_preview": text[:2000],
        "line_tables": line_payload,
        "text_tables": text_payload,
    }


def extract_camelot(pdf: Path, page_number: int) -> dict:
    results = {}
    for flavor in ("lattice", "stream"):
        started = time.monotonic()
        try:
            tables = camelot.read_pdf(str(pdf), pages=str(page_number), flavor=flavor)
            payload_tables = []
            for table in tables:
                matrix = normalize_matrix(table.df.values.tolist())
                payload_tables.append(
                    {
                        "shape": matrix_shape(matrix),
                        "accuracy": float(table.parsing_report.get("accuracy", 0.0)),
                        "whitespace": float(table.parsing_report.get("whitespace", 0.0)),
                        "matrix": matrix,
                    }
                )
            results[flavor] = {
                "ok": True,
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "table_count": len(payload_tables),
                "tables": payload_tables,
            }
        except Exception as exc:  # pragma: no cover - evidence path
            results[flavor] = {
                "ok": False,
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "error": f"{type(exc).__name__}: {exc}",
                "table_count": 0,
                "tables": [],
            }
    return {"engine": "camelot", "page": page_number, "flavors": results}


def write_one_page_pdf(pdf: Path, page_number: int, output: Path) -> None:
    reader = PdfReader(str(pdf))
    writer = PdfWriter()
    writer.add_page(reader.pages[page_number - 1])
    with output.open("wb") as handle:
        writer.write(handle)


def compare(native: dict, camelot_payload: dict) -> dict:
    native_line = native["line_tables"][0]["matrix"] if native["line_tables"] else []
    native_text = native["text_tables"][0]["matrix"] if native["text_tables"] else []
    camelot_lattice = (
        camelot_payload["flavors"]["lattice"]["tables"][0]["matrix"]
        if camelot_payload["flavors"]["lattice"]["tables"]
        else []
    )
    shape_native_line = matrix_shape(native_line)
    shape_native_text = matrix_shape(native_text)
    shape_camelot_lattice = matrix_shape(camelot_lattice)
    same_shape = shape_native_line == shape_native_text == shape_camelot_lattice
    exact_native_match = native_line == native_text
    exact_camelot_match = native_line == camelot_lattice
    return {
        "expected_page_content": "figure_plus_formal_specification_table",
        "native_line_shape": shape_native_line,
        "native_text_shape": shape_native_text,
        "camelot_lattice_shape": shape_camelot_lattice,
        "same_shape": same_shape,
        "exact_native_line_vs_text": exact_native_match,
        "exact_native_line_vs_camelot_lattice": exact_camelot_match,
        "auto_save_allowed": bool(same_shape and exact_native_match and exact_camelot_match),
        "decision": (
            "PASS_MACHINE_AGREEMENT_REQUIRES_HUMAN_QA_BEFORE_LIVE_IMPORT"
            if same_shape and exact_native_match and exact_camelot_match
            else "FAIL_CLOSED_REQUIRES_REVIEW"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--page", type=int, default=7)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pdf_sha = sha256_file(args.pdf)
    native = extract_native(args.pdf, args.page)
    camelot_payload = extract_camelot(args.pdf, args.page)
    one_page_pdf = args.out_dir / "page7_one_page.pdf"
    write_one_page_pdf(args.pdf, args.page, one_page_pdf)

    image = Image.open(args.image)
    table_bbox = tuple(native["line_tables"][0]["bbox"]) if native["line_tables"] else None
    crops = {}
    if table_bbox is not None:
        table_px = pdf_bbox_to_px(
            table_bbox,
            native["page_width"],
            native["page_height"],
            image.width,
            image.height,
        )
        crops["table"] = crop_and_hash(image, table_px, args.out_dir / "crops" / "page7_table.png")
        figure_px = detect_figure_bbox(args.image, table_px)
        crops["figure"] = crop_and_hash(image, figure_px, args.out_dir / "crops" / "page7_figure.png")

    comparison = compare(native, camelot_payload)
    payload = {
        "action": "R05-A08",
        "source_pdf": str(args.pdf),
        "source_pdf_sha256": pdf_sha,
        "page": args.page,
        "image": str(args.image),
        "image_sha256": sha256_file(args.image),
        "one_page_pdf": str(one_page_pdf),
        "one_page_pdf_sha256": sha256_file(one_page_pdf),
        "native": native,
        "camelot": camelot_payload,
        "crops": crops,
        "comparison": comparison,
    }
    output = args.out_dir / "r05_a08_page7_native_camelot_figure.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
