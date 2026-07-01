from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "supabase/migrations/20260629222000_029_hybrid_search_version_gate.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260629222000_029_hybrid_search_version_gate_down.sql"


class HybridSearchVersionGateMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8").lower()
        cls.rollback = ROLLBACK.read_text(encoding="utf-8").lower()

    def test_forward_recreates_exact_function_signature(self):
        self.assertIn("create or replace function public.hybrid_search_v3", self.forward)
        for fragment in [
            "p_query_embedding extensions.vector",
            "p_query_text text default ''",
            "p_match_threshold double precision default 0.4",
            "p_match_count integer default 8",
            "p_user_id uuid default null",
            "p_min_quality numeric default 0.3",
            "stable",
            "security definer",
            "set search_path to 'pg_catalog', 'public', 'extensions'",
        ]:
            self.assertIn(fragment, self.forward)

    def test_forward_requires_current_approved_document_version_evidence(self):
        required = [
            "join public.document_versions dv",
            "dv.id = d.current_version_id",
            "dv.document_id = d.id",
            "dv.version_label = dc.document_version",
            "dv.approved_for_ai_use = true",
            "dv.approval_evidence_status = 'verified'",
            "dv.hash_status = 'verified'",
            "dv.license_status in ('allowed', 'curated')",
            "dv.parse_status in ('success', 'partial')",
            "dv.binary_sha256 is not null",
            "dv.content_sha256 is not null",
            "dv.parse_quality_score is not null",
            "dv.parsed_at is not null",
            "dv.retired_at is null",
        ]
        for fragment in required:
            self.assertIn(fragment, self.forward)

    def test_forward_requires_chunk_gate_and_embedding_presence(self):
        self.assertIn("dc.status = 'approved_for_ai_use'::public.document_status", self.forward)
        self.assertIn("dc.embedding is not null", self.forward)
        self.assertIn("public.document_is_currently_valid", self.forward)
        self.assertIn("not (d.is_ai_translated = true", self.forward)

    def test_no_audit_or_data_mutation_in_function_migration(self):
        body_without_function_ddl = re.sub(
            r"create or replace function public\.hybrid_search_v3[\s\S]*?\$function\$;",
            "",
            self.forward,
        )
        forbidden = [
            "insert into public.audit_log",
            "update public.audit_log",
            "delete from public.audit_log",
            "truncate",
            "update public.document_chunks",
            "update public.document_versions",
            "delete from public.document_chunks",
            "delete from public.document_versions",
        ]
        for fragment in forbidden:
            self.assertNotIn(fragment, body_without_function_ddl)

    def test_rollback_restores_pre_029_without_version_gate(self):
        self.assertIn("create or replace function public.hybrid_search_v3", self.rollback)
        self.assertNotIn("join public.document_versions dv", self.rollback)
        self.assertNotIn("dv.approved_for_ai_use = true", self.rollback)
        self.assertIn("public.document_is_currently_valid", self.rollback)


if __name__ == "__main__":
    unittest.main()
