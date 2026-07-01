#!/usr/bin/env python3
"""Static guard for the legacy root dashboard HTML rendering."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_APP = ROOT / "js/app.js"


class LegacyFrontendXssTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LEGACY_APP.read_text(encoding="utf-8")

    def test_dynamic_api_and_db_values_are_not_interpolated_raw(self) -> None:
        forbidden_raw_interpolations = [
            "${e.message}",
            "${s.message}",
            "${r.error",
            "${r.conflict_warning}",
            "${r.language_warning}",
            "${r.answer}",
            "${r.disclaimer",
            "${s.document_code",
            "${s.version",
            "${s.language_code",
            "${s.page_number",
            "${s.section_code",
            "${s.section_title",
            "${s.source_type",
            "${d.document_code}",
            "${d.document_title}",
            "${d.document_type}",
            "${d.language_code}",
            "${d.version}",
            "${d.status}",
            "${l.user_email",
            "${l.user_role",
            "${l.action_type",
            "${l.input_summary",
            "${l.document_code",
            "${c.label}",
            "${c.detail}",
        ]
        for pattern in forbidden_raw_interpolations:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, self.source)

    def test_html_helpers_exist_for_text_class_and_score_rendering(self) -> None:
        self.assertIn("function escapeHtml(t)", self.source)
        self.assertIn("function safeClass(value, fallback)", self.source)
        self.assertIn("function formatScore(value)", self.source)

    def test_legacy_dashboard_keeps_functionality_instead_of_removing_tables(self) -> None:
        required_fragments = [
            "serviceStatus",
            "statsGrid",
            "sources-table",
            "doc-table",
            "audit_log",
            "security-check",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)


if __name__ == "__main__":
    unittest.main()
