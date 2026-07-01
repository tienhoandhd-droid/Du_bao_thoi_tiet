#!/usr/bin/env python3
"""Compare three table extractors and deny auto-save on any structural mismatch."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NUMERIC_RE = re.compile(r"\b\d+(?:[.,]\d+)*(?:\s*(?:%|days?|months?|µm|um|mg|g|kg|ml|mL|L))?\b", re.I)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def paddle_summary(data: dict) -> dict:
    table_count = int(data.get("table_count", 0))
    rows = []
    columns = []
    texts: list[str] = []
    for result in data.get("results", []):
        candidate = result.get("res", result) if isinstance(result, dict) else {}
        for table in candidate.get("table_res_list", []) or []:
            html = str(table.get("pred_html", ""))
            rows.append(html.count("<tr>"))
            columns.append(max((segment.count("<td") for segment in html.split("<tr>")), default=0))
            texts.extend((table.get("table_ocr_pred", {}) or {}).get("rec_texts", []) or [])
    return {"table_count": table_count, "rows": rows, "columns": columns, "texts": texts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docling", required=True, type=Path)
    parser.add_argument("--paddle", required=True, type=Path)
    parser.add_argument("--docling-400", required=True, type=Path)
    parser.add_argument("--paddle-400", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    docling = load(args.docling)
    paddle = load(args.paddle)
    docling_400 = load(args.docling_400)
    paddle_400 = load(args.paddle_400)
    native = load(args.native)
    paddle_metrics = paddle_summary(paddle)
    paddle_400_metrics = paddle_summary(paddle_400)

    docling_shapes = [
        [table["rows"], table["columns"]] for table in docling.get("tables", [])
    ]
    native_shape = [native.get("semantic_rows", 0), native.get("semantic_columns", 0)]
    native_lines = [
        line
        for record in native.get("left_records", []) + native.get("right_records", [])
        for line in record.get("lines", [])
    ]
    docling_cells = [
        str(cell)
        for table in docling.get("tables", [])
        for row in table.get("cells", [])
        for cell in row
    ]
    all_text = "\n".join(docling_cells + paddle_metrics["texts"] + native_lines)
    result = {
        "page": 10,
        "candidate_type": "borderless_bilingual_aligned_glossary",
        "ground_truth_available": False,
        "engines": {
            "docling": {"table_count": docling.get("table_count", 0), "shapes": docling_shapes},
            "paddle": paddle_metrics,
            "docling_400dpi": {
                "table_count": docling_400.get("table_count", 0),
                "shapes": [
                    [table["rows"], table["columns"]]
                    for table in docling_400.get("tables", [])
                ],
            },
            "paddle_400dpi": paddle_400_metrics,
            "native": {
                "formal_line_table_count": native.get("formal_line_table_count", 0),
                "text_strategy_table_count": native.get("text_strategy_table_count", 0),
                "text_strategy_shapes": native.get("text_strategy_shapes", []),
                "semantic_shape": native_shape,
                "anchor_pairs_match": native.get("anchor_pairs_match", False),
            },
        },
        "numeric_tokens_observed": sorted(set(NUMERIC_RE.findall(all_text))),
    }
    structural_agreement = (
        docling.get("table_count", 0) == 1
        and paddle_metrics["table_count"] == 1
        and docling_400.get("table_count", 0) == 1
        and paddle_400_metrics["table_count"] == 1
        and docling_shapes == [native_shape]
        and paddle_metrics["rows"] == [native_shape[0]]
        and paddle_metrics["columns"] == [native_shape[1]]
        and native.get("anchor_pairs_match", False)
    )
    result["decision"] = {
        "structural_agreement": structural_agreement,
        "auto_save_allowed": False,
        "retry_400dpi_completed": True,
        "retry_resolved_disagreement": structural_agreement,
        "reason": (
            "Machine structure agreement is incomplete and no authoritative ground truth exists."
            if not structural_agreement
            else "Machine agreement exists but human source-image QA is still mandatory."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["decision"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
