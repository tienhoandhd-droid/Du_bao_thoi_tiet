#!/usr/bin/env python3
"""Run PaddleOCR General Table Recognition V2 on one approved page image."""

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
    parser.add_argument("--model-dir", required=True, type=Path)
    args = parser.parse_args()

    args.model_dir.mkdir(parents=True, exist_ok=True)
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
    for result in results:
        candidate = result.get("res", result) if isinstance(result, dict) else {}
        table_count += len(candidate.get("table_res_list", []) or [])
    payload = {
        "engine": "PaddleOCR/PP-TableMagic",
        "engine_version": "paddleocr-3.7.0/paddlepaddle-3.3.1",
        "page": 10,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "table_count": table_count,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
