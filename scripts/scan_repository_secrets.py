#!/usr/bin/env python3
"""Quét dấu hiệu secret theo path/rule mà không in nội dung khớp."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from validate_release_manifest import SECRET_RULES


ALLOWED_SUFFIXES = {".json", ".js", ".md", ".py", ".sql", ".ts", ".tsx", ".yaml", ".yml"}
EXCLUDED_PARTS = {".git", ".codex", "dist", "node_modules", "__pycache__"}


def candidate_files(root: Path, inputs: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for raw in inputs:
        path = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise ValueError(f"đường dẫn thoát khỏi repository: {raw}")
        paths = (path.rglob("*")) if path.is_dir() else (path,)
        for candidate in paths:
            if (
                candidate.is_file()
                and candidate.suffix.lower() in ALLOWED_SUFFIXES
                and not EXCLUDED_PARTS.intersection(candidate.relative_to(root).parts)
                and candidate not in seen
            ):
                seen.add(candidate)
                yield candidate


def scan(root: Path, inputs: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for path in candidate_files(root, inputs):
        content = path.read_text(encoding="utf-8", errors="replace")
        display = str(path.relative_to(root))
        for rule_name, pattern in SECRET_RULES:
            if pattern.search(content):
                errors.append(f"{display}: phát hiện dấu hiệu secret ({rule_name})")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="File/thư mục cần quét")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repo_root.resolve()
    try:
        errors = scan(root, args.paths)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if errors:
        print(f"FAIL: secret scan có {len(errors)} cảnh báo", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("PASS: không phát hiện dấu hiệu secret")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
