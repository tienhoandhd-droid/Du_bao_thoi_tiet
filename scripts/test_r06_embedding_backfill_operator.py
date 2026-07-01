import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import r06_embedding_backfill_operator as op


def chunk(chunk_id: str, document_code: str = "GMP-SOP-001", index: int = 0) -> dict:
    return {
        "id": chunk_id,
        "document_id": "11111111-1111-4111-8111-111111111111",
        "document_code": document_code,
        "document_version": "01",
        "language_code": "vi",
        "chunk_index": index,
        "content": f"Nội dung kiểm thử {index}",
    }


def embedding(index: int, dimensions: int = 3) -> dict:
    return {"index": index, "embedding": [float(index), 0.1, 0.2][:dimensions]}


class R06EmbeddingBackfillOperatorTests(unittest.TestCase):
    def test_validate_chunks_rejects_duplicate_or_wrong_count(self):
        rows = [
            chunk("22222222-2222-4222-8222-222222222222"),
            chunk("22222222-2222-4222-8222-222222222222"),
        ]
        with self.assertRaises(op.BackfillValidationError):
            op.validate_chunks(rows, expected_count=2)
        with self.assertRaises(op.BackfillValidationError):
            op.validate_chunks(rows[:1], expected_count=2)

    def test_validate_embeddings_rejects_dimension_mismatch(self):
        response = {"data": [{"index": 0, "embedding": [0.0, 0.1]}]}
        with self.assertRaises(op.BackfillValidationError):
            op.validate_embeddings(response, expected_count=1, dimensions=3)

    def test_build_sql_is_idempotent_and_audited(self):
        chunks = op.validate_chunks(
            [
                chunk("22222222-2222-4222-8222-222222222222", "GMP-SOP-001", 0),
                chunk("33333333-3333-4333-8333-333333333333", "GMP-SOP-001", 1),
            ],
            expected_count=2,
        )
        embeddings = op.validate_embeddings(
            {"data": [embedding(0), embedding(1)]},
            expected_count=2,
            dimensions=3,
        )
        sql = op.build_sql(op.build_payload(chunks, embeddings), "text-embedding-3-small", 3)
        self.assertIn("update public.document_chunks dc", sql.lower())
        self.assertIn("dc.embedding is null", sql.lower())
        self.assertIn("payload.embedding::extensions.vector", sql.lower())
        self.assertIn("public.write_audit_log", sql.lower())
        self.assertIn("'document_index'::public.audit_action", sql.lower())
        self.assertNotIn("delete from public.audit_log", sql.lower())
        self.assertNotIn("update public.audit_log", sql.lower())
        self.assertNotIn("truncate", sql.lower())

    def test_cli_chunks_only_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            chunks_path = Path(tmp) / "chunks.json"
            chunks_path.write_text(
                json.dumps(
                    [
                        chunk("22222222-2222-4222-8222-222222222222", index=0),
                        chunk("33333333-3333-4333-8333-333333333333", index=1),
                    ]
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "python3",
                    "scripts/r06_embedding_backfill_operator.py",
                    "--chunks-json",
                    str(chunks_path),
                    "--expected-count",
                    "2",
                    "--dimensions",
                    "3",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "DRY_RUN_CHUNKS_ONLY")
            self.assertEqual(payload["chunks"], 2)


if __name__ == "__main__":
    unittest.main()
