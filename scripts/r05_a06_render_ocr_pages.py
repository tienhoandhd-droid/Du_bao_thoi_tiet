#!/usr/bin/env python3
"""Render exactly three approved PDF pages at 150 DPI for R05-A06."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pypdfium2 as pdfium


APPROVED_PAGES_ONE_BASED = (1, 9, 18)
APPROVED_DPI = 150


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input_pdf.is_file():
        raise SystemExit(f"Missing PDF: {args.input_pdf}")

    document = pdfium.PdfDocument(str(args.input_pdf))
    if len(document) != 18:
        raise SystemExit(f"R05-A06 expected 18 pages, got {len(document)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scale = APPROVED_DPI / 72.0
    rendered: list[dict[str, object]] = []

    for page_number in APPROVED_PAGES_ONE_BASED:
        page = document[page_number - 1]
        bitmap = page.render(scale=scale, rotation=0)
        image = bitmap.to_pil().convert("RGB")
        output_path = args.output_dir / f"r05_a06_page_{page_number:02d}_150dpi.png"
        image.save(output_path, format="PNG", optimize=True)
        rendered.append(
            {
                "page_number": page_number,
                "dpi": APPROVED_DPI,
                "width_px": image.width,
                "height_px": image.height,
                "mode": image.mode,
                "output_path": str(output_path),
                "output_bytes": output_path.stat().st_size,
            }
        )
        bitmap.close()
        page.close()

    document.close()
    print(json.dumps({"rendered_pages": rendered}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
