#!/usr/bin/env python3
"""Kiểm tra release manifest CRAVE mà không thay đổi repository hay runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(r"^[0-9]+(?:\.[0-9]+){0,2}$")
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
PROMPT_FILE = re.compile(r"^v([0-9]+(?:\.[0-9]+){0,2})\.md$")
VERSION_PREFIX = re.compile(r"^(\d{3})_")
EXPECTED_PROJECT_ID = "bdttccztjtrcaztjgkot"

# Chỉ báo rule/path; tuyệt đối không đưa matched value vào lỗi.
SECRET_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("tavily-key", re.compile(r"tvly-[A-Za-z0-9_-]{20,}")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("long-jwt-or-service-key", re.compile(r"\beyJ[A-Za-z0-9_-]{180,}")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)(?:password|api[_-]?key|secret|token)\s*[:=]\s*[\"'][^\"']{12,}[\"']"
        ),
    ),
)


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class ManifestValidator:
    def __init__(self, manifest_path: Path, repo_root: Path) -> None:
        self.manifest_path = manifest_path.resolve()
        self.repo_root = repo_root.resolve()
        self.errors: list[str] = []
        self.declared_files: set[Path] = set()

    def error(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: {message}")

    def required_dict(self, parent: Any, key: str, location: str) -> dict[str, Any]:
        value = parent.get(key) if isinstance(parent, dict) else None
        if not isinstance(value, dict):
            self.error(f"{location}.{key}", "phải là object")
            return {}
        return value

    def required_list(self, parent: Any, key: str, location: str) -> list[Any]:
        value = parent.get(key) if isinstance(parent, dict) else None
        if not isinstance(value, list) or not value:
            self.error(f"{location}.{key}", "phải là array không rỗng")
            return []
        return value

    def required_string(self, parent: Any, key: str, location: str) -> str:
        value = parent.get(key) if isinstance(parent, dict) else None
        if not isinstance(value, str) or not value.strip():
            self.error(f"{location}.{key}", "phải là chuỗi không rỗng")
            return ""
        return value.strip()

    def safe_file(self, raw_path: str, location: str) -> Path | None:
        if not raw_path:
            return None
        relative = Path(raw_path)
        if relative.is_absolute():
            self.error(location, "đường dẫn phải tương đối với repository")
            return None
        candidate = (self.repo_root / relative).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError:
            self.error(location, "đường dẫn thoát khỏi repository")
            return None
        if not candidate.is_file():
            self.error(location, f"không tìm thấy file: {raw_path}")
            return None
        self.declared_files.add(candidate)
        return candidate

    def verify_hash(self, path: Path | None, expected: str, location: str) -> None:
        if not HEX_64.fullmatch(expected):
            self.error(location, "phải là SHA-256 64 ký tự hex chữ thường")
            return
        if path is None:
            return
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            self.error(location, "không khớp nội dung file")

    def validate_migrations(self, data: dict[str, Any]) -> None:
        section = self.required_dict(data, "supabase", "manifest")
        project_id = self.required_string(section, "projectId", "supabase")
        if project_id and project_id != EXPECTED_PROJECT_ID:
            self.error("supabase.projectId", "không phải project CRAVE được phép")
        current = self.required_string(section, "currentMigrationVersion", "supabase")
        migrations = self.required_list(section, "migrations", "supabase")
        versions: set[str] = set()
        for index, item in enumerate(migrations):
            location = f"supabase.migrations[{index}]"
            if not isinstance(item, dict):
                self.error(location, "phải là object")
                continue
            version = self.required_string(item, "version", location)
            if version in versions:
                self.error(f"{location}.version", "bị trùng")
            versions.add(version)
            up_raw = self.required_string(item, "up", location)
            down_raw = self.required_string(item, "down", location)
            up = self.safe_file(up_raw, f"{location}.up")
            down = self.safe_file(down_raw, f"{location}.down")
            for field, raw in (("up", up_raw), ("down", down_raw)):
                match = VERSION_PREFIX.match(Path(raw).name) if raw else None
                if not match or match.group(1) != version:
                    self.error(f"{location}.{field}", "số file không khớp version")
            if up_raw and down_raw:
                expected_down_stem = f"{Path(up_raw).stem}_down"
                if Path(down_raw).stem != expected_down_stem:
                    self.error(
                        f"{location}.down",
                        "tên rollback phải bằng tên migration kèm hậu tố _down",
                    )
            self.verify_hash(
                up,
                self.required_string(item, "upSha256", location),
                f"{location}.upSha256",
            )
            self.verify_hash(
                down,
                self.required_string(item, "downSha256", location),
                f"{location}.downSha256",
            )
        if current and current not in versions:
            self.error("supabase.currentMigrationVersion", "không có trong migrations")

    def validate_workflows(self, data: dict[str, Any]) -> None:
        section = self.required_dict(data, "n8n", "manifest")
        expected = section.get("expectedWorkflowCount")
        if not isinstance(expected, int) or expected < 1:
            self.error("n8n.expectedWorkflowCount", "phải là số nguyên dương")
        workflows = self.required_list(section, "workflows", "n8n")
        if isinstance(expected, int) and len(workflows) != expected:
            self.error("n8n.workflows", "số lượng không khớp expectedWorkflowCount")
        numbers: set[str] = set()
        ids: set[str] = set()
        for index, item in enumerate(workflows):
            location = f"n8n.workflows[{index}]"
            if not isinstance(item, dict):
                self.error(location, "phải là object")
                continue
            number = self.required_string(item, "workflowNumber", location)
            workflow_id = self.required_string(item, "id", location)
            active_version = self.required_string(item, "activeVersionId", location)
            if not re.fullmatch(r"\d{2}", number):
                self.error(f"{location}.workflowNumber", "phải có đúng 2 chữ số")
            if number in numbers:
                self.error(f"{location}.workflowNumber", "bị trùng")
            if workflow_id in ids:
                self.error(f"{location}.id", "bị trùng")
            numbers.add(number)
            ids.add(workflow_id)
            if active_version and not UUID.fullmatch(active_version):
                self.error(f"{location}.activeVersionId", "phải là UUID")
            raw = self.required_string(item, "file", location)
            path = self.safe_file(raw, f"{location}.file")
            if raw and not Path(raw).name.startswith(f"TKTL-WF-{number}-"):
                self.error(f"{location}.file", "tên file không khớp workflowNumber")
            self.verify_hash(
                path,
                self.required_string(item, "sha256", location),
                f"{location}.sha256",
            )

    def validate_prompts(self, data: dict[str, Any]) -> None:
        prompts = self.required_list(data, "prompts", "manifest")
        keys: set[str] = set()
        for index, item in enumerate(prompts):
            location = f"prompts[{index}]"
            if not isinstance(item, dict):
                self.error(location, "phải là object")
                continue
            key = self.required_string(item, "key", location)
            version = self.required_string(item, "version", location)
            if key in keys:
                self.error(f"{location}.key", "bị trùng")
            keys.add(key)
            if version and not SEMVER.fullmatch(version):
                self.error(f"{location}.version", "không đúng định dạng version")
            raw = self.required_string(item, "file", location)
            path = self.safe_file(raw, f"{location}.file")
            parts = Path(raw).parts if raw else ()
            name_match = PROMPT_FILE.fullmatch(Path(raw).name) if raw else None
            if len(parts) < 3 or parts[0] != "prompts" or parts[-2] != key:
                self.error(f"{location}.file", "phải nằm tại prompts/<key>/")
            if not name_match or name_match.group(1) != version:
                self.error(f"{location}.file", "tên file phải là v<version>.md")
            self.verify_hash(
                path,
                self.required_string(item, "sha256", location),
                f"{location}.sha256",
            )

    def validate_model_and_dataset(self, data: dict[str, Any]) -> None:
        model = self.required_dict(data, "model", "manifest")
        for key in ("provider", "name", "version"):
            self.required_string(model, key, "model")
        dataset = self.required_dict(data, "dataset", "manifest")
        for key in ("name", "version"):
            self.required_string(dataset, key, "dataset")
        raw = self.required_string(dataset, "file", "dataset")
        path = self.safe_file(raw, "dataset.file")
        self.verify_hash(
            path,
            self.required_string(dataset, "sha256", "dataset"),
            "dataset.sha256",
        )

    def scan_secrets(self) -> None:
        paths = {self.manifest_path, *self.declared_files}
        for path in sorted(paths):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            display = str(path.relative_to(self.repo_root))
            for rule_name, pattern in SECRET_RULES:
                if pattern.search(content):
                    self.error(display, f"phát hiện dấu hiệu secret ({rule_name})")

    def run(self) -> ValidationResult:
        if not self.manifest_path.is_file():
            return ValidationResult((f"manifest: không tìm thấy {self.manifest_path}",))
        try:
            self.manifest_path.relative_to(self.repo_root)
        except ValueError:
            return ValidationResult(("manifest: phải nằm trong repository root",))
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ValidationResult((f"manifest: JSON không hợp lệ ({exc.__class__.__name__})",))
        if not isinstance(data, dict):
            return ValidationResult(("manifest: root phải là object",))

        for key in ("manifestVersion", "releaseId", "generatedAt", "project"):
            self.required_string(data, key, "manifest")
        git = self.required_dict(data, "git", "manifest")
        sha = self.required_string(git, "sha", "git")
        self.required_string(git, "branch", "git")
        if sha and not HEX_40.fullmatch(sha):
            self.error("git.sha", "phải là Git SHA đầy đủ 40 ký tự hex chữ thường")

        self.validate_migrations(data)
        self.validate_workflows(data)
        self.validate_prompts(data)
        self.validate_model_and_dataset(data)
        self.scan_secrets()
        return ValidationResult(tuple(self.errors))


def validate(manifest_path: Path, repo_root: Path) -> ValidationResult:
    return ManifestValidator(manifest_path, repo_root).run()


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Đường dẫn manifest JSON")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Root dùng để resolve đường dẫn artifact (mặc định: thư mục hiện tại)",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    result = validate(args.manifest, args.repo_root)
    if result.ok:
        print("PASS: release manifest hợp lệ")
        return 0
    print(f"FAIL: release manifest có {len(result.errors)} lỗi", file=sys.stderr)
    for error in result.errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
