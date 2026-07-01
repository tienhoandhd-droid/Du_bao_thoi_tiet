"""Regression checks for R05-A41 hybrid_search_v3 authenticated EXECUTE grant."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260701080500_030d_grant_hybrid_search_v3_authenticated_execute.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260701080500_030d_grant_hybrid_search_v3_authenticated_execute_down.sql"


class R05A41HybridSearchV3ExecuteGrantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.migration = MIGRATION.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.combined = f"{cls.migration}\n{cls.rollback}"

    def test_migration_targets_exact_hybrid_search_v3_signature(self) -> None:
        self.assertIn("public.hybrid_search_v3", self.migration)
        self.assertIn("to_regprocedure(", self.migration)
        self.assertIn(
            "public.hybrid_search_v3(extensions.vector,text,double precision,integer,uuid,text,text,text,integer,text,numeric)",
            self.migration,
        )
        self.assertIn("extensions.vector", self.migration)

    def test_only_authenticated_gets_execute_and_anon_public_stay_denied(self) -> None:
        normalized = " ".join(self.migration.lower().split())
        self.assertIn("grant execute on function public.hybrid_search_v3", normalized)
        self.assertIn("to authenticated", normalized)
        self.assertIn("revoke execute on function public.hybrid_search_v3", normalized)
        self.assertIn("from anon", normalized)
        self.assertIn("from public", normalized)

    def test_rollback_removes_only_authenticated_execute(self) -> None:
        normalized = " ".join(self.rollback.lower().split())
        self.assertIn("revoke execute on function public.hybrid_search_v3", normalized)
        self.assertIn("from authenticated", normalized)
        self.assertNotIn("from service_role", normalized)
        self.assertNotIn("drop function", normalized)

    def test_no_data_seed_or_dangerous_mutation(self) -> None:
        lowered = self.combined.lower()
        forbidden_fragments = (
            "insert into public.",
            "update public.",
            "delete from public.",
            "truncate ",
            "alter table ",
            "drop table ",
            "drop function ",
            "service_role key",
            "jwt_secret",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, lowered)


if __name__ == "__main__":
    unittest.main()
