#!/usr/bin/env python3
"""Tests for R05 raw parse probe."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "r05_raw_parse_probe.py"


class R05RawParseProbeTests(unittest.TestCase):
    def test_non_pdf_is_fail_closed_with_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("hello GMP", encoding="utf-8")
            record = json.loads(
                subprocess.check_output(["python3", str(SCRIPT), str(path)], text=True)
            )["records"][0]
        self.assertEqual(record["file_name"], "sample.txt")
        self.assertEqual(record["sha256"], hashlib.sha256(b"hello GMP").hexdigest())
        self.assertFalse(record["is_pdf"])
        self.assertEqual(record["parse_quality_status"], "not_pdf_fail_closed")

    def test_fake_pdf_without_text_never_passes_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.pdf"
            path.write_bytes(b"%PDF-1.7\n%%EOF\n")
            completed = subprocess.run(
                ["python3", str(SCRIPT), str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
            record = json.loads(completed.stdout)["records"][0]
        self.assertTrue(record["is_pdf"])
        self.assertNotEqual(record["parse_quality_status"], "pass_local_sample")


if __name__ == "__main__":
    unittest.main()
