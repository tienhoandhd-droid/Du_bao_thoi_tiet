#!/usr/bin/env python3
"""Tests for the R05-A20 owner promotion gate."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r05_a20_owner_promotion_gate.py"
A19_REPORT = ROOT / "work/r05_a19_controlled_draft_corpus_hash_parse_report.json"
CURRENT_PLAN = ROOT / "work/r05_a20_owner_promotion_plan.csv"
CURRENT_REPORT = ROOT / "work/r05_a20_owner_promotion_gate_report.json"
DRAFT_CORPUS = ROOT / "output/pdf/r05_controlled_draft_corpus"

REQUIRED_CODES = [
    *(f"GMP-SOP-{idx:03d}" for idx in range(1, 11)),
    "VQ-QT-003",
    "WHO-TRS-996",
]
DECISION_FIELDS = (
    "technical_sme_decision",
    "qa_gmp_decision",
    "data_integrity_decision",
    "license_owner_decision",
    "document_owner_decision",
    "source_control_decision",
)
REVIEWER_FIELDS = (
    ("technical_sme_name", "technical_sme_reviewed_at"),
    ("qa_gmp_name", "qa_gmp_reviewed_at"),
    ("data_integrity_name", "data_integrity_reviewed_at"),
    ("license_owner_name", "license_owner_reviewed_at"),
    ("document_owner_name", "document_owner_reviewed_at"),
    ("source_control_name", "source_control_reviewed_at"),
)
PROMOTE_DECISION = "PROMOTE_TO_CORRECTED_CORPUS_PENDING_HASH_PARSE_PLAN"


def run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def approve_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approved: list[dict[str, str]] = []
    for row in rows:
        updated = dict(row)
        for decision_field in DECISION_FIELDS:
            updated[decision_field] = "APPROVED"
        for reviewer_field, reviewed_at_field in REVIEWER_FIELDS:
            updated[reviewer_field] = f"{reviewer_field}_human"
            updated[reviewed_at_field] = "2026-06-30T12:00:00+07:00"
        updated["promotion_decision"] = PROMOTE_DECISION
        updated["corrected_corpus_file_name"] = f"{updated['document_code']} approved.pdf"
        updated["corrected_corpus_sha256"] = "0" * 64
        updated["promotion_notes"] = "Human approved test fixture."
        approved.append(updated)
    return approved


class R05A20OwnerPromotionGateTest(unittest.TestCase):
    def test_write_template_fails_closed_with_pending_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = Path(temp_dir) / "promotion_plan.csv"
            output = Path(temp_dir) / "report.json"

            result = run_gate("--review-plan", str(plan), "--output", str(output), "--write-template")

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            rows = read_csv(plan)

        self.assertEqual(report["decision"], "FAIL_CLOSED_OWNER_APPROVAL_REQUIRED")
        self.assertEqual(report["promotion_plan"]["summary"]["row_count"], 12)
        self.assertEqual(report["promotion_plan"]["summary"]["complete_human_approved_rows"], 0)
        self.assertEqual({row["document_code"] for row in rows}, set(REQUIRED_CODES))
        self.assertTrue(all(row["promotion_decision"] == "DENY_UNTIL_ALL_REQUIRED_REVIEWS_PASS" for row in rows))
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})

    def test_approved_plan_rejects_ai_or_codex_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = Path(temp_dir) / "promotion_plan.csv"
            output = Path(temp_dir) / "report.json"
            initial = run_gate("--review-plan", str(plan), "--output", str(output), "--write-template")
            self.assertNotEqual(initial.returncode, 0)

            rows = approve_rows(read_csv(plan))
            rows[0]["qa_gmp_name"] = "Codex GPT"
            write_csv(plan, rows)

            result = run_gate("--review-plan", str(plan), "--output", str(output))

            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["decision"], "FAIL_CLOSED_OWNER_APPROVAL_REQUIRED")
        self.assertIn("cannot be an AI/Codex/OpenAI reviewer", "\n".join(report["promotion_plan"]["errors"]))

    def test_approved_plan_with_draft_folder_fails_corrected_corpus_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = Path(temp_dir) / "promotion_plan.csv"
            output = Path(temp_dir) / "report.json"
            initial = run_gate("--review-plan", str(plan), "--output", str(output), "--write-template")
            self.assertNotEqual(initial.returncode, 0)

            rows = approve_rows(read_csv(plan))
            for row in rows:
                row["corrected_corpus_file_name"] = row["source_file_name"]
                row["corrected_corpus_sha256"] = row["source_sha256"]
            write_csv(plan, rows)

            result = run_gate(
                "--review-plan",
                str(plan),
                "--corrected-corpus-dir",
                str(DRAFT_CORPUS),
                "--output",
                str(output),
            )

            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["decision"], "FAIL_CLOSED_CORRECTED_CORPUS_INVALID")
        self.assertIn("controlled draft marker", "\n".join(report["corrected_corpus"]["errors"]))

    def test_fully_approved_plan_without_corpus_is_ready_to_build_corrected_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = Path(temp_dir) / "promotion_plan.csv"
            output = Path(temp_dir) / "report.json"
            missing_corpus = Path(temp_dir) / "missing-corpus"
            initial = run_gate("--review-plan", str(plan), "--output", str(output), "--write-template")
            self.assertNotEqual(initial.returncode, 0)

            rows = approve_rows(read_csv(plan))
            write_csv(plan, rows)

            result = run_gate(
                "--review-plan",
                str(plan),
                "--corrected-corpus-dir",
                str(missing_corpus),
                "--output",
                str(output),
            )

            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["decision"], "READY_FOR_CORRECTED_CORPUS_BUILD_PLAN")
        self.assertFalse(report["corrected_corpus"]["exists"])
        self.assertEqual(report["promotion_plan"]["summary"]["complete_human_approved_rows"], 12)

    def test_fully_approved_plan_with_clean_corrected_corpus_is_hash_parse_plan_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            plan = base / "promotion_plan.csv"
            output = base / "report.json"
            corpus = base / "corrected-corpus"
            corpus.mkdir()
            initial = run_gate("--review-plan", str(plan), "--output", str(output), "--write-template")
            self.assertNotEqual(initial.returncode, 0)

            rows = approve_rows(read_csv(plan))
            for row in rows:
                code = row["document_code"]
                file_name = f"{code} approved.pdf"
                payload = b"%PDF-1.7\n" + code.encode("ascii") + b" owner approved fixture\n%%EOF\n"
                (corpus / file_name).write_bytes(payload)
                row["corrected_corpus_file_name"] = file_name
                row["corrected_corpus_sha256"] = sha256_bytes(payload)
            write_csv(plan, rows)

            result = run_gate(
                "--review-plan",
                str(plan),
                "--corrected-corpus-dir",
                str(corpus),
                "--output",
                str(output),
            )

            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["decision"], "READY_FOR_CONTROLLED_CORPUS_HASH_PARSE_PLAN")
        self.assertTrue(report["corrected_corpus"]["ok"])
        self.assertEqual(report["promotion_plan"]["summary"]["complete_human_approved_rows"], 12)

    def test_retained_current_plan_requires_owner_approval(self) -> None:
        report = json.loads(CURRENT_REPORT.read_text(encoding="utf-8"))
        rows = read_csv(CURRENT_PLAN)

        self.assertEqual(report["rhythm"], "R05-A20")
        self.assertEqual(report["decision"], "FAIL_CLOSED_OWNER_APPROVAL_REQUIRED")
        self.assertEqual(report["promotion_plan"]["summary"]["row_count"], 12)
        self.assertEqual(report["promotion_plan"]["summary"]["complete_human_approved_rows"], 0)
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row["technical_sme_decision"] == "PENDING" for row in rows))
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertEqual(report["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(report["blockers"]["BLK-004"], "OPEN")


if __name__ == "__main__":
    unittest.main()
