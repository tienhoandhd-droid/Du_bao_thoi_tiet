from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "supabase/migrations/20260630174500_030_document_chunk_version_lineage.sql"
ROLLBACK = ROOT / "supabase/rollbacks/20260630174500_030_document_chunk_version_lineage_down.sql"


class DocumentChunkVersionLineageMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8").lower()
        cls.rollback = ROLLBACK.read_text(encoding="utf-8").lower()

    def test_preflight_requires_exact_existing_contract(self):
        for fragment in [
            "to_regclass('public.documents')",
            "to_regclass('public.document_versions')",
            "to_regclass('public.document_chunks')",
            "array['id', 'document_id', 'document_version', 'chunk_index']",
            "not like 'crave-030:%'",
        ]:
            self.assertIn(fragment, self.forward)

    def test_backfill_is_exact_and_asserted_before_not_null(self):
        for fragment in [
            "update public.document_chunks dc",
            "set document_version_id = dv.id",
            "dv.document_id = dc.document_id",
            "dv.version_label = dc.document_version",
            "ambiguous_pairs",
            "unmatched_chunks",
            "invalid_existing_links",
            "alter column document_version_id set not null",
        ]:
            self.assertIn(fragment, self.forward)
        self.assertLess(
            self.forward.index("do $backfill_assert$"),
            self.forward.index("alter column document_version_id set not null"),
        )

    def test_fk_and_trigger_enforce_same_document_and_version_label(self):
        for fragment in [
            "constraint document_chunks_document_version_id_fkey",
            "references public.document_versions(id)",
            "on update restrict",
            "on delete restrict",
            "create or replace function public.crave_validate_document_chunk_version_lineage()",
            "linked_document_id is distinct from new.document_id",
            "linked_version_label is distinct from new.document_version",
            "before insert or update of document_id, document_version, document_version_id",
        ]:
            self.assertIn(fragment, self.forward)

    def test_migration_does_not_fake_approval_or_delete_evidence(self):
        for fragment in [
            "approved_for_ai_use = true",
            "update public.document_versions",
            "delete from public.document_chunks",
            "delete from public.document_versions",
            "truncate",
        ]:
            self.assertNotIn(fragment, self.forward)

    def test_rollback_is_guarded_and_preserves_chunk_rows(self):
        for fragment in [
            "unmatched_chunks",
            "ambiguous_pairs",
            "legacy compatibility unsafe",
            "drop trigger if exists document_chunks_validate_version_lineage",
            "drop constraint if exists document_chunks_document_version_id_fkey",
            "drop column document_version_id",
        ]:
            self.assertIn(fragment, self.rollback)
        self.assertIsNone(re.search(r"\b(delete|truncate)\b", self.rollback))


if __name__ == "__main__":
    unittest.main()
