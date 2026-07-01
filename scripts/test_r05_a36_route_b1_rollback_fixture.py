#!/usr/bin/env python3
"""Static safety tests for R05-A36 Route B1 rollback-only fixture."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "work/r05_a36_route_b1_blk006_rollback_fixture_live.sql"
RESIDUE = ROOT / "work/r05_a36_route_b1_zero_residue_readonly.sql"


class R05A36RouteB1RollbackFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE.read_text(encoding="utf-8")
        cls.fixture_lower = cls.fixture.lower()
        cls.residue = RESIDUE.read_text(encoding="utf-8")
        cls.residue_lower = cls.residue.lower()

    def test_fixture_has_explicit_transaction_and_no_commit_statement(self) -> None:
        begin_matches = list(re.finditer(r"(?im)^begin;\s*$", self.fixture))
        rollback_matches = list(re.finditer(r"(?im)^rollback;\s*$", self.fixture))
        commit_matches = list(re.finditer(r"(?im)^commit;\s*$", self.fixture))
        self.assertEqual(len(begin_matches), 1)
        self.assertEqual(len(rollback_matches), 1)
        self.assertEqual(len(commit_matches), 0)
        self.assertLess(begin_matches[0].start(), rollback_matches[0].start())

    def test_six_fixed_fixture_ids_are_present_in_fixture_and_residue_probe(self) -> None:
        for suffix in range(1, 7):
            fixture_id = f"a3600000-0000-4000-8000-{suffix:012d}"
            self.assertIn(fixture_id, self.fixture)
            self.assertIn(fixture_id, self.residue)

    def test_fixture_covers_full_positive_lineage(self) -> None:
        for relation in (
            "public.documents",
            "public.raw_files",
            "public.document_versions",
            "public.document_chunks",
            "public.ai_queries",
            "public.ai_query_sources",
        ):
            self.assertIn(f"insert into {relation}", self.fixture_lower)
        self.assertIn("public.hybrid_search_v3", self.fixture_lower)
        self.assertIn("grounded", self.fixture_lower)
        self.assertIn("citation_rank", self.fixture_lower)
        self.assertIn("dc.document_version_id", self.fixture_lower)
        self.assertIn("d.current_version_id = dv.id", self.fixture_lower)
        self.assertIn("dv.raw_file_id = rf.id", self.fixture_lower)

    def test_positive_assertions_fail_closed_before_rollback(self) -> None:
        assertion_pos = self.fixture_lower.index("do $positive_assertions$")
        rollback_pos = re.search(r"(?im)^rollback;\s*$", self.fixture).start()
        self.assertLess(assertion_pos, rollback_pos)
        self.assertIn("if retrieved_count <> 1", self.fixture_lower)
        self.assertIn("or exact_retrieval_count <> 1", self.fixture_lower)
        self.assertIn("or grounded_source_count <> 1", self.fixture_lower)
        self.assertIn("or valid_lineage_count <> 1", self.fixture_lower)
        self.assertIn("raise exception", self.fixture_lower[assertion_pos:rollback_pos])

    def test_baseline_must_be_zero_and_embedding_dimension_is_pinned(self) -> None:
        self.assertIn("baseline_retrieval_count <> 0", self.fixture_lower)
        self.assertIn("extensions.vector_dims(embedding)", self.fixture_lower)
        self.assertIn("<> 1536", self.fixture_lower)
        self.assertIn("0.999", self.fixture)

    def test_generated_content_tsv_is_not_written_explicitly(self) -> None:
        chunk_insert = re.search(
            r"insert into public\.document_chunks\s*\((.*?)\)\s*select",
            self.fixture_lower,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(chunk_insert)
        self.assertNotIn("content_tsv", chunk_insert.group(1))

    def test_final_result_is_after_rollback_and_requires_zero_residue(self) -> None:
        rollback_pos = re.search(r"(?im)^rollback;\s*$", self.fixture).start()
        final_gate_pos = self.fixture_lower.index(
            "r05_a36_route_b1_blk006_rollback_fixture",
            rollback_pos,
        )
        self.assertLess(rollback_pos, final_gate_pos)
        self.assertIn(
            "pass_positive_citation_asserted_and_zero_residue",
            self.fixture_lower[rollback_pos:],
        )
        self.assertIn("commit_present", self.fixture_lower[rollback_pos:])
        self.assertIn("'commit_present', false", self.fixture_lower[rollback_pos:])

    def test_independent_residue_probe_is_read_only(self) -> None:
        for forbidden in (
            "insert into",
            "update ",
            "delete from",
            "truncate ",
            "alter table",
            "create table",
            "drop table",
        ):
            self.assertNotIn(forbidden, self.residue_lower)
        self.assertIn("pass_zero_residue", self.residue_lower)
        self.assertIn("fail_fixture_residue_found", self.residue_lower)

    def test_fixture_does_not_touch_n8n_or_git(self) -> None:
        for forbidden_statement in (
            "update_workflow",
            "execute_workflow",
            "publish_workflow",
            "archive_workflow",
            "git push",
            "git commit",
        ):
            self.assertNotIn(forbidden_statement, self.fixture_lower)
        self.assertIn(
            "no n8n agent execution",
            self.fixture_lower,
        )


if __name__ == "__main__":
    unittest.main()
