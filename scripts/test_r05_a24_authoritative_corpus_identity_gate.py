#!/usr/bin/env python3
"""Tests for the R05-A24 authoritative corpus identity gate."""

from __future__ import annotations

import json
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import r05_a24_authoritative_corpus_identity_gate as gate  # noqa: E402

SCRIPT = ROOT / "scripts/r05_a24_authoritative_corpus_identity_gate.py"
REPORT = ROOT / "work/r05_a24_authoritative_corpus_identity_gate_report.json"
CHECKPOINT = ROOT / "docs/checkpoints/search-upgrade/R05-A24-authoritative-corpus-identity-gate.md"
MANIFEST = ROOT / "docs/checkpoints/search-upgrade/R05-A24-authoritative-corpus-identity-gate-manifest.json"


def run_operator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class R05A24AuthoritativeCorpusIdentityGateTest(unittest.TestCase):
    def test_marker_detection_catches_reference_library_content(self) -> None:
        text = "BS EN ISO 10993 Biological evaluation of medical devices"

        markers = gate.detect_reference_markers(text)

        self.assertIn("ISO_10993", markers)
        self.assertIn("BS_EN_ISO", markers)
        self.assertIn("BIOLOGICAL_EVALUATION_MEDICAL_DEVICES", markers)

    def test_default_current_corpus_fails_closed_for_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"

            result = run_operator("--output", str(output))
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        self.assertFalse(report["intake"]["ok"])
        self.assertEqual(report["summary"]["audit_source"], "actual_filename_unmapped_pdfs")
        self.assertEqual(report["summary"]["intake_record_count"], 0)
        self.assertEqual(report["summary"]["record_count"], 12)
        self.assertEqual(report["summary"]["random_light_sample_hash_matches"], 2)
        self.assertEqual(report["summary"]["forbidden_reference_marker_records"], 12)
        self.assertEqual(report["summary"]["records_identity_fail_closed"], 12)
        self.assertEqual(report["summary"]["records_with_expected_code_visible"], 0)
        self.assertIn("Authoritative corpus intake failed.", report["identity_errors"])
        self.assertIn("actual-filename PDF(s) were inspected", "\n".join(report["identity_errors"]))
        self.assertIn("source identity evidence", "\n".join(report["identity_warnings"]))
        self.assertFalse(report["quality_controls"]["filename_code_convention_required"])
        self.assertNotIn("do not match any required document code", "\n".join(report["intake"]["errors"]))
        self.assertIn("not bound by the local mapping manifest", "\n".join(report["intake"]["errors"]))
        self.assertEqual(report["local_mapping_csv"], str(gate.DEFAULT_LOCAL_MAPPING))
        self.assertEqual(report["remote_operations"], {"git": [], "n8n": [], "supabase": []})
        self.assertEqual(report["blockers"]["BLK-003"], "OPEN")
        self.assertEqual(report["blockers"]["BLK-004"], "OPEN")

    def test_matching_logical_document_filenames_pass_with_authoritative_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus = base / "corpus"
            corpus.mkdir()
            mapping = base / "mapping.csv"
            output = base / "report.json"
            rows: list[dict[str, str]] = []
            names = [f"{code} approved source.pdf" for code in gate.REQUIRED_CODES]
            for index, (code, name) in enumerate(zip(gate.REQUIRED_CODES, names)):
                (corpus / name).write_bytes(
                    b"%PDF-1.7\nidentity-" + str(index).encode("ascii") + b"\n%%EOF\n"
                )
                rows.append(
                    {
                        "document_code": code,
                        "file_name": name,
                        "status": "AUTHORITATIVE_CONFIRMED",
                        "mapping_notes": f"Owner-confirmed identity for {code}",
                    }
                )
            with mapping.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            result = run_operator(
                "--corpus-dir",
                str(corpus),
                "--local-mapping-csv",
                str(mapping),
                "--output",
                str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["record_count"], 12)
        self.assertEqual(report["summary"]["records_confirmed_by_authoritative_manifest"], 12)
        self.assertEqual(report["summary"]["records_identity_fail_closed"], 0)
        self.assertTrue(
            all(
                record["identity_decision"] == "IDENTITY_CONFIRMED_BY_AUTHORITATIVE_MANIFEST"
                for record in report["records"]
            )
        )

    def test_external_references_require_catalog_reconciliation_even_with_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            corpus = base / "corpus"
            corpus.mkdir()
            mapping = base / "mapping.csv"
            output = base / "report.json"
            rows: list[dict[str, str]] = []
            for index, code in enumerate(gate.REQUIRED_CODES, start=1):
                name = f"PDA Technical Report reference {index}.pdf"
                (corpus / name).write_bytes(
                    b"%PDF-1.7\nexternal-reference-"
                    + str(index).encode("ascii")
                    + b"\n%%EOF\n"
                )
                rows.append(
                    {
                        "document_code": code,
                        "file_name": name,
                        "status": "AUTHORITATIVE_CONFIRMED",
                        "mapping_notes": f"Generic owner note for {code}",
                    }
                )
            with mapping.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            result = run_operator(
                "--corpus-dir",
                str(corpus),
                "--local-mapping-csv",
                str(mapping),
                "--output",
                str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"]["records_requiring_catalog_reconciliation"], 12)
        self.assertEqual(report["summary"]["records_confirmed_by_authoritative_manifest"], 0)
        self.assertIn("generic owner mapping manifest cannot", "\n".join(report["identity_errors"]))
        self.assertTrue(report["quality_controls"]["mapping_manifest_does_not_override_semantic_identity"])

    def test_retained_report_checkpoint_and_manifest_match_fail_closed_state(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")

        self.assertEqual(report["rhythm"], "R05-A24")
        self.assertEqual(report["decision"], "FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH")
        self.assertIn("FAIL_CLOSED_CORPUS_IDENTITY_MISMATCH", checkpoint)
        self.assertEqual(manifest["rhythm"], "R05-A24")
        self.assertEqual(manifest["decision"], report["decision"])
        self.assertEqual(
            manifest["identitySummary"]["auditSource"],
            report["summary"]["audit_source"],
        )
        self.assertEqual(
            manifest["identitySummary"]["recordCount"],
            report["summary"]["record_count"],
        )
        self.assertEqual(
            manifest["identitySummary"]["randomLightSampleHashMatches"],
            report["summary"]["random_light_sample_hash_matches"],
        )
        self.assertEqual(
            manifest["identitySummary"]["forbiddenReferenceMarkerRecords"],
            report["summary"]["forbidden_reference_marker_records"],
        )
        self.assertEqual(
            manifest["identitySummary"]["recordsIdentityFailClosed"],
            report["summary"]["records_identity_fail_closed"],
        )
        self.assertIn("12/12", checkpoint)
        self.assertIn("2/12", checkpoint)
        self.assertEqual(manifest["supabase"]["operations"], [])
        self.assertEqual(manifest["n8n"]["operations"], [])
        self.assertEqual(manifest["git"]["operations"], [])


if __name__ == "__main__":
    unittest.main()
