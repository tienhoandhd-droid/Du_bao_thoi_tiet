#!/usr/bin/env python3
"""Compare three OCR outputs without treating engine consensus as ground truth."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:[.,]\d+)*(?:%|°[CF])?|[^\W\s]", re.UNICODE)
NUMERIC_RE = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:\s?(?:%|°[CF]|mg|g|kg|µg|ug|mL|ml|L|mm|cm|m|h|min|s))?", re.I)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def page_number(source: str) -> int:
    match = re.search(r"page_(\d+)", source)
    if not match:
        raise ValueError(f"page number missing from {source}")
    return int(match.group(1))


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tesseract(paths: list[Path]) -> list[dict]:
    pages = []
    for path in paths:
        lines: dict[tuple[str, ...], list[dict]] = {}
        with path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                text = row["text"].strip()
                confidence = float(row["conf"])
                if not text or confidence < 0:
                    continue
                key = (row["block_num"], row["par_num"], row["line_num"])
                lines.setdefault(key, []).append(row)
        normalized_lines = []
        for words in lines.values():
            left = min(int(word["left"]) for word in words)
            top = min(int(word["top"]) for word in words)
            right = max(int(word["left"]) + int(word["width"]) for word in words)
            bottom = max(int(word["top"]) + int(word["height"]) for word in words)
            width = int(words[0]["width"]) if False else 1240
            height = 1755
            normalized_lines.append(
                {
                    "text": " ".join(word["text"] for word in words),
                    "confidence": sum(float(word["conf"]) for word in words) / (100 * len(words)),
                    "bbox": [left / width, top / height, (right - left) / width, (bottom - top) / height],
                }
            )
        pages.append(
            {
                "engine": "Tesseract",
                "engineVersion": "5.x",
                "source": path.name.replace(".tsv", ".png"),
                "width": 1240,
                "height": 1755,
                "lines": normalized_lines,
            }
        )
    return pages


def text_of(page: dict) -> str:
    return "\n".join(line["text"] for line in page["lines"])


def metrics(left: str, right: str) -> dict:
    left_norm, right_norm = normalize(left), normalize(right)
    left_tokens, right_tokens = TOKEN_RE.findall(left_norm), TOKEN_RE.findall(right_norm)
    left_set, right_set = set(left_tokens), set(right_tokens)
    union = left_set | right_set
    similarity = SequenceMatcher(None, left_norm, right_norm).ratio()
    return {
        "characterSimilarity": round(similarity, 6),
        "characterDisagreementRate": round(1 - similarity, 6),
        "tokenJaccard": round(len(left_set & right_set) / len(union), 6) if union else 1.0,
        "leftCharacters": len(left_norm),
        "rightCharacters": len(right_norm),
        "leftWords": len(left_tokens),
        "rightWords": len(right_tokens),
        "leftNumericTokens": sorted(set(NUMERIC_RE.findall(left_norm))),
        "rightNumericTokens": sorted(set(NUMERIC_RE.findall(right_norm))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--third", required=True, type=Path)
    parser.add_argument("--rapid", required=True, type=Path)
    parser.add_argument("--tesseract", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    collections = {
        "EasyOCR": load_json(args.third),
        "RapidOCR": load_json(args.rapid),
        "Tesseract": load_tesseract(args.tesseract),
    }
    pages = sorted({page_number(page["source"]) for values in collections.values() for page in values})
    indexed = {
        engine: {page_number(page["source"]): page for page in values}
        for engine, values in collections.items()
    }
    output = {"groundTruthAvailable": False, "pages": {}}
    engines = list(collections)
    for number in pages:
        page_result = {"engines": {}, "pairwise": {}}
        for engine in engines:
            page = indexed[engine][number]
            text = text_of(page)
            confidences = [float(line["confidence"]) for line in page["lines"]]
            page_result["engines"][engine] = {
                "characters": len(normalize(text)),
                "words": len(TOKEN_RE.findall(normalize(text))),
                "lines": len(page["lines"]),
                "meanConfidence": round(sum(confidences) / len(confidences), 6) if confidences else 0,
                "numericTokens": sorted(set(NUMERIC_RE.findall(normalize(text)))),
                "text": text,
            }
        for index, left in enumerate(engines):
            for right in engines[index + 1 :]:
                key = f"{left} <> {right}"
                page_result["pairwise"][key] = metrics(
                    page_result["engines"][left]["text"],
                    page_result["engines"][right]["text"],
                )
        numeric_sets = [set(page_result["engines"][engine]["numericTokens"]) for engine in engines]
        page_result["allEngineNumericIntersection"] = sorted(set.intersection(*numeric_sets))
        page_result["numericUnion"] = sorted(set.union(*numeric_sets))
        page_result["requiresReview"] = any(
            pair["characterDisagreementRate"] > 0.05 or pair["tokenJaccard"] < 0.95
            for pair in page_result["pairwise"].values()
        ) or len(page_result["allEngineNumericIntersection"]) != len(page_result["numericUnion"])
        output["pages"][str(number)] = page_result

    output["decision"] = {
        "autoSaveAllowed": False,
        "reason": "No authoritative ground truth; engine consensus cannot prove correctness.",
        "reviewPages": [number for number in pages if output["pages"][str(number)]["requiresReview"]],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["decision"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
