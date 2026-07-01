#!/usr/bin/env python3
"""Run the temporary EasyOCR engine and emit normalized OCR JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
import easyocr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    args = parser.parse_args()

    args.model_dir.mkdir(parents=True, exist_ok=True)
    reader = easyocr.Reader(
        ["en"],
        gpu=False,
        model_storage_directory=str(args.model_dir),
        download_enabled=True,
    )
    pages = []
    for image_path in args.images:
        width, height = Image.open(image_path).size
        result = reader.readtext(str(image_path), detail=1, paragraph=False)
        lines = []
        for box, text, confidence in result:
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            lines.append(
                {
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [
                        min(xs) / width,
                        min(ys) / height,
                        (max(xs) - min(xs)) / width,
                        (max(ys) - min(ys)) / height,
                    ],
                }
            )
        pages.append(
            {
                "engine": "EasyOCR",
                "engineVersion": "easyocr-1.7.2",
                "source": image_path.name,
                "width": width,
                "height": height,
                "lines": lines,
            }
        )
    print(json.dumps(pages, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
