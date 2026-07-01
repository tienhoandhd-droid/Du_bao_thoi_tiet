from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "supabase/migrations/20260629192100_028_document_versions_acl_hardening.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260629192100_028_document_versions_acl_hardening_down.sql"
CATALOG_TEST = ROOT / "supabase/tests/028_document_versions_acl_hardening_test.sql"


class DocumentVersionsAclHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.catalog_test = CATALOG_TEST.read_text(encoding="utf-8")

    def test_scope_is_acl_only(self):
        self.assertIn("20260629192100_028_document_versions_acl_hardening", self.forward)
        self.assertNotIn("create table", self.forward.lower())
        self.assertNotIn("alter table", self.forward.lower())
        self.assertNotIn("insert into", self.forward.lower())
        self.assertNotIn("update public", self.forward.lower())
        self.assertNotIn("delete from", self.forward.lower())

    def test_revoke_then_minimal_grant(self):
        self.assertIn(
            "from public, anon, authenticated, service_role",
            self.forward,
        )
        self.assertIn(
            "grant select, insert, update on table public.document_versions",
            self.forward,
        )
        self.assertNotIn("grant all", self.forward.lower())
        self.assertNotIn("grant delete", self.forward.lower())

    def test_both_roles_have_exact_negative_checks(self):
        for role in ("authenticated", "service_role"):
            for privilege in ("DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
                self.assertIn(
                    f"has_table_privilege('{role}','public.document_versions','{privilege}')",
                    self.forward,
                )
                self.assertIn(
                    f"has_table_privilege('{role}','public.document_versions','{privilege}')",
                    self.catalog_test,
                )

    def test_rollback_honestly_restores_prior_acl(self):
        self.assertIn("grant all on table public.document_versions", self.rollback.lower())
        self.assertIn("exact approval", self.rollback.lower())


if __name__ == "__main__":
    unittest.main()
