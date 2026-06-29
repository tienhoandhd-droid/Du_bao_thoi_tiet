#!/usr/bin/env python3
"""Kiểm thử dương/âm cho release manifest bằng dữ liệu hoàn toàn giả."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "eval" / "fixtures" / "release-package"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_manifest", REPO_ROOT / "scripts" / "validate_release_manifest.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ReleaseManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "package"
        shutil.copytree(FIXTURE_ROOT, self.root)
        self.manifest_path = self.root / "release-manifest.valid.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def load_manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save_manifest(self, data: dict) -> None:
        self.manifest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def validate(self):
        return VALIDATOR.validate(self.manifest_path, self.root)

    def assert_error_contains(self, result, expected: str) -> None:
        self.assertFalse(result.ok)
        self.assertTrue(
            any(expected in error for error in result.errors),
            msg=f"Không thấy {expected!r} trong: {result.errors}",
        )

    def test_valid_fixture_passes(self) -> None:
        self.assertTrue(self.validate().ok)

    def test_missing_rollback_fails(self) -> None:
        (self.root / "supabase" / "rollbacks" / "001_example_down.sql").unlink()
        self.assert_error_contains(self.validate(), "không tìm thấy file")

    def test_missing_workflow_fails(self) -> None:
        (self.root / "n8n" / "workflows" / "TKTL-WF-01-fixture.json").unlink()
        self.assert_error_contains(self.validate(), "n8n.workflows[0].file")

    def test_rollback_name_mismatch_fails(self) -> None:
        data = self.load_manifest()
        old = self.root / data["supabase"]["migrations"][0]["down"]
        new = old.with_name("001_other_down.sql")
        old.rename(new)
        data["supabase"]["migrations"][0]["down"] = str(new.relative_to(self.root))
        self.save_manifest(data)
        self.assert_error_contains(self.validate(), "tên rollback")

    def test_unversioned_prompt_fails(self) -> None:
        data = self.load_manifest()
        old = self.root / data["prompts"][0]["file"]
        new = old.with_name("current.md")
        old.rename(new)
        data["prompts"][0]["file"] = str(new.relative_to(self.root))
        self.save_manifest(data)
        self.assert_error_contains(self.validate(), "tên file phải là v<version>.md")

    def test_secret_is_detected_without_echoing_value(self) -> None:
        data = self.load_manifest()
        workflow = self.root / data["n8n"]["workflows"][0]["file"]
        fake_secret = "tvly-" + ("Z" * 24)
        workflow.write_text(workflow.read_text(encoding="utf-8") + fake_secret, encoding="utf-8")
        data["n8n"]["workflows"][0]["sha256"] = hashlib.sha256(workflow.read_bytes()).hexdigest()
        self.save_manifest(data)
        result = self.validate()
        self.assert_error_contains(result, "phát hiện dấu hiệu secret")
        self.assertNotIn(fake_secret, "\n".join(result.errors))

    def test_hash_mismatch_fails(self) -> None:
        data = self.load_manifest()
        data["dataset"]["sha256"] = "0" * 64
        self.save_manifest(data)
        self.assert_error_contains(self.validate(), "dataset.sha256")

    def test_short_git_sha_fails(self) -> None:
        data = self.load_manifest()
        data["git"]["sha"] = "abc1234"
        self.save_manifest(data)
        self.assert_error_contains(self.validate(), "Git SHA đầy đủ")


if __name__ == "__main__":
    unittest.main()
