#!/usr/bin/env python3
"""Evaluate the R05-A13 remaining P0 closure gate.

This local-only gate determines whether the repository has enough authoritative
corpus input to proceed from BLK-003/004 toward citation runtime and agent gates.
It does not download files, call Supabase, execute n8n, or mutate remote state.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from r05_authoritative_corpus_intake import (
    IntakeResult,
    validate_corpus_dir,
    validate_mapping_csv,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "work/r05_authoritative_12_file_mapping.csv"
DEFAULT_CORPUS = ROOT / "work/r05_authoritative_corpus"

DEPENDENCY_ORDER = (
    "BLK-003: validate authoritative 12-file mapping or corrected corpus input",
    "BLK-003: collect controlled binary byte-count and SHA-256 evidence",
    "BLK-003: link each raw binary to the current document version",
    "BLK-004: generate bounded parse/OCR/table/figure evidence per authoritative version",
    "BLK-004: record human reviewer decision for disputed or critical content",
    "BLK-006: run runtime query/citation checks only after verified retrieval can return grounded evidence",
    "BLK-007: run U10-U15 gates and agent canary only after citation/runtime gates pass",
)

STOP_CONDITIONS = (
    "No authoritative mapping/corrected corpus is present.",
    "Any required document code is missing or duplicated.",
    "Any Drive file ID is a placeholder or reused across required document codes.",
    "Any selected file is an archive or unrelated reference-library substitute.",
    "Any parser path returns success without extractable evidence, disagreement data, or reviewer decision.",
    "Any citation test would run while hybrid_search_v3 is intentionally fail-closed.",
    "Any agent canary is requested before U10-U15 PASS evidence exists.",
    "Any Supabase/n8n/Git remote mutation is attempted without a fresh exact approval.",
)


@dataclass(frozen=True)
class InputCheck:
    mode: str
    path: str
    exists: bool
    ok: bool
    decision: str
    errors: list[str]
    warnings: list[str]
    record_count: int

    @classmethod
    def missing(cls, mode: str, path: Path) -> "InputCheck":
        return cls(
            mode=mode,
            path=str(path),
            exists=False,
            ok=False,
            decision="MISSING",
            errors=[f"{mode} input not found: {path}"],
            warnings=[],
            record_count=0,
        )

    @classmethod
    def from_intake(cls, mode: str, path: Path, result: IntakeResult) -> "InputCheck":
        return cls(
            mode=mode,
            path=str(path),
            exists=True,
            ok=result.ok,
            decision="PASS" if result.ok else "FAIL_CLOSED",
            errors=result.errors,
            warnings=result.warnings,
            record_count=len(result.records),
        )


def evaluate_inputs(mapping_csv: Path, corpus_dir: Path) -> list[InputCheck]:
    checks: list[InputCheck] = []

    if mapping_csv.exists():
        checks.append(InputCheck.from_intake("mapping_csv", mapping_csv, validate_mapping_csv(mapping_csv)))
    else:
        checks.append(InputCheck.missing("mapping_csv", mapping_csv))

    if corpus_dir.exists():
        checks.append(InputCheck.from_intake("corpus_dir", corpus_dir, validate_corpus_dir(corpus_dir)))
    else:
        checks.append(InputCheck.missing("corpus_dir", corpus_dir))

    return checks


def build_report(mapping_csv: Path, corpus_dir: Path) -> dict[str, Any]:
    input_checks = evaluate_inputs(mapping_csv, corpus_dir)
    passing_inputs = [check for check in input_checks if check.ok]

    if passing_inputs:
        decision = "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN"
        rationale = (
            "At least one authoritative input mode validates. BLK-003/004 are not "
            "closed yet; the next step is a separately approved controlled evidence "
            "run for binary lineage, parse evidence, reviewer decisions and current "
            "document-version linkage."
        )
        next_allowed_local_steps = [
            "Prepare exact controlled corpus evidence plan from the validated input.",
            "Run only local/static tests until a fresh n8n/Supabase approval is granted.",
            "Keep BLK-006/007 blocked until BLK-003/004 closure evidence exists.",
        ]
    else:
        decision = "FAIL_CLOSED_INPUT_REQUIRED"
        rationale = (
            "No authoritative 12-file mapping or corrected corpus folder is available. "
            "Random light samples and reference-library probes must not be promoted to "
            "production corpus evidence."
        )
        next_allowed_local_steps = [
            "Wait for work/r05_authoritative_12_file_mapping.csv or work/r05_authoritative_corpus.",
            "Re-run this local gate after authoritative input is placed.",
            "Do not execute citation runtime or agent canaries while retrieval remains fail-closed.",
        ]

    return {
        "rhythm": "R05-A13",
        "gate": "P0",
        "ok": bool(passing_inputs),
        "decision": decision,
        "rationale": rationale,
        "input_checks": [asdict(check) for check in input_checks],
        "blockers": {
            "BLK-003": "OPEN",
            "BLK-004": "OPEN",
            "BLK-006": "OPEN",
            "BLK-007": "OPEN",
        },
        "dependency_order": list(DEPENDENCY_ORDER),
        "next_allowed_local_steps": next_allowed_local_steps,
        "stop_conditions": list(STOP_CONDITIONS),
        "remote_operations": {
            "supabase": [],
            "n8n": [],
            "git": [],
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping-csv", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(args.mapping_csv, args.corpus_dir)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")

    print(serialized)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
