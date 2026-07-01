#!/usr/bin/env python3
"""Extract the page-10 borderless bilingual row structure from the PDF text layer."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pdfplumber


ANCHOR_RE = re.compile(r"^2\.[3-8]$")


def words_to_lines(words: list[dict], tolerance: float = 2.5) -> list[dict]:
    lines: list[dict] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        target = next(
            (line for line in lines if abs(line["top"] - word["top"]) <= tolerance),
            None,
        )
        if target is None:
            target = {"top": word["top"], "words": []}
            lines.append(target)
        target["words"].append(word)
    for line in lines:
        line["words"].sort(key=lambda item: item["x0"])
        line["text"] = " ".join(item["text"] for item in line["words"])
    return sorted(lines, key=lambda item: item["top"])


def records_for_column(words: list[dict], x0: float, x1: float) -> list[dict]:
    column_words = [word for word in words if x0 <= word["x0"] < x1]
    anchors = sorted(
        [word for word in column_words if ANCHOR_RE.fullmatch(word["text"])],
        key=lambda item: item["top"],
    )
    records = []
    for position, anchor in enumerate(anchors):
        end_top = anchors[position + 1]["top"] if position + 1 < len(anchors) else float("inf")
        block = words_to_lines(
            [
                word
                for word in column_words
                if word["top"] >= anchor["top"] - 1 and word["top"] < end_top - 1
            ]
        )
        records.append(
            {
                "anchor": anchor["text"],
                "top": round(float(anchor["top"]), 3),
                "lines": [line["text"] for line in block],
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    started = time.monotonic()
    with pdfplumber.open(args.pdf) as pdf:
        page = pdf.pages[9]
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        default_tables = page.find_tables()
        text_tables = page.find_tables(
            table_settings={
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 5,
            }
        )
        split_x = 270.0
        left = records_for_column(words, 0, split_x)
        right = records_for_column(words, split_x, page.width + 1)
        text_strategy_shapes = []
        for table in text_tables:
            matrix = table.extract()
            text_strategy_shapes.append(
                [len(matrix), max((len(row) for row in matrix), default=0)]
            )

    payload = {
        "engine": "pdfplumber/native-text",
        "engine_version": "pdfplumber-bundled",
        "page": 10,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "formal_line_table_count": len(default_tables),
        "text_strategy_table_count": len(text_tables),
        "text_strategy_shapes": text_strategy_shapes,
        "semantic_rows": len(left),
        "semantic_columns": 2,
        "left_records": left,
        "right_records": right,
        "anchor_pairs_match": len(left) == 6
        and [item["anchor"] for item in left] == [item["anchor"] for item in right],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
