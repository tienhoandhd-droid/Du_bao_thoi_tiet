#!/usr/bin/env python3
"""Run the temporary RapidOCR engine and emit normalized OCR JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
from rapidocr_onnxruntime import RapidOCR


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    args = parser.parse_args()

    engine = RapidOCR()
    pages = []
    for image_path in args.images:
        width, height = Image.open(image_path).size
        result, elapsed = engine(str(image_path))
        lines = []
        for box, text, confidence in result or []:
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
                "engine": "RapidOCR",
                "engineVersion": "rapidocr_onnxruntime-1.4.4",
                "source": image_path.name,
                "width": width,
                "height": height,
                "elapsedSeconds": elapsed,
                "lines": lines,
            }
        )
    print(json.dumps(pages, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
