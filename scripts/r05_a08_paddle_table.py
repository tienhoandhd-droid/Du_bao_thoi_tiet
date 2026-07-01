#!/usr/bin/env python3
"""Run PaddleOCR PP-TableMagic / table pipeline for R05-A08."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from paddleocr import TableRecognitionPipelineV2


def jsonable(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--page", type=int, default=7)
    args = parser.parse_args()

    started = time.monotonic()
    pipeline = TableRecognitionPipelineV2(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        device="cpu",
        cpu_threads=4,
    )
    outputs = list(
        pipeline.predict(
            str(args.image),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_layout_detection=True,
            use_ocr_model=True,
        )
    )
    results = []
    for output in outputs:
        raw = getattr(output, "json", output)
        if callable(raw):
            raw = raw()
        results.append(jsonable(raw))

    table_count = 0
    html_shapes = []
    rec_texts = []
    for result in results:
        candidate = result.get("res", result) if isinstance(result, dict) else {}
        for table in candidate.get("table_res_list", []) or []:
            table_count += 1
            html = str(table.get("pred_html", ""))
            rows = html.count("<tr")
            columns = max((segment.count("<td") + segment.count("<th") for segment in html.split("<tr")), default=0)
            html_shapes.append([rows, columns])
            rec_texts.extend((table.get("table_ocr_pred", {}) or {}).get("rec_texts", []) or [])

    payload = {
        "engine": "PaddleOCR/PP-TableMagic",
        "engine_version": "paddleocr-3.7.0/paddlepaddle-3.3.1",
        "page": args.page,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "table_count": table_count,
        "html_shapes": html_shapes,
        "rec_texts": rec_texts,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"table_count": table_count, "html_shapes": html_shapes, "rec_texts": len(rec_texts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
