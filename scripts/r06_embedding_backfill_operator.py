#!/usr/bin/env python3
"""R06-A02 source-only helper for controlled embedding backfill.

This script does not call OpenAI and does not connect to Supabase. It validates
an exported chunk inventory plus an OpenAI embeddings response, then emits an
idempotent SQL transaction that updates only missing embeddings by chunk id and
appends audit rows through public.write_audit_log().
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_EXPECTED_COUNT = 65
DEFAULT_DIMENSIONS = 1536
DEFAULT_MODEL = "text-embedding-3-small"
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


class BackfillValidationError(ValueError):
    """Raised when a backfill payload is unsafe or inconsistent."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("rows", "data", "chunks"):
            if isinstance(data.get(key), list):
                return data[key]
    raise BackfillValidationError("Input JSON must be a list or contain rows/data/chunks list")


def validate_chunks(rows: list[dict[str, Any]], expected_count: int) -> list[dict[str, Any]]:
    if len(rows) != expected_count:
        raise BackfillValidationError(f"Expected {expected_count} chunk rows, got {len(rows)}")

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        chunk_id = str(row.get("id") or "").strip()
        if not UUID_RE.match(chunk_id):
            raise BackfillValidationError(f"Row {index} has invalid chunk id: {chunk_id!r}")
        if chunk_id in seen_ids:
            raise BackfillValidationError(f"Duplicate chunk id: {chunk_id}")
        seen_ids.add(chunk_id)

        content = str(row.get("content") or "").strip()
        if not content:
            raise BackfillValidationError(f"Row {index} has empty content")

        document_id = str(row.get("document_id") or "").strip()
        if document_id and not UUID_RE.match(document_id):
            raise BackfillValidationError(f"Row {index} has invalid document_id: {document_id!r}")

        normalized.append(
            {
                "id": chunk_id,
                "document_id": document_id or None,
                "document_code": str(row.get("document_code") or "").strip(),
                "document_version": str(row.get("document_version") or "").strip(),
                "language_code": str(row.get("language_code") or "").strip() or None,
                "chunk_index": int(row.get("chunk_index") or 0),
                "content": content,
            }
        )
    return normalized


def validate_embeddings(response: dict[str, Any], expected_count: int, dimensions: int) -> list[list[float]]:
    data = response.get("data")
    if not isinstance(data, list):
        raise BackfillValidationError("OpenAI response must contain data list")
    if len(data) != expected_count:
        raise BackfillValidationError(f"Expected {expected_count} embeddings, got {len(data)}")

    ordered: list[list[float] | None] = [None] * expected_count
    seen_indexes: set[int] = set()
    for fallback_index, item in enumerate(data):
        if not isinstance(item, dict):
            raise BackfillValidationError(f"Embedding item {fallback_index} must be an object")
        item_index = int(item.get("index", fallback_index))
        if item_index < 0 or item_index >= expected_count:
            raise BackfillValidationError(f"Embedding index out of range: {item_index}")
        if item_index in seen_indexes:
            raise BackfillValidationError(f"Duplicate embedding index: {item_index}")
        seen_indexes.add(item_index)

        embedding = item.get("embedding")
        if not isinstance(embedding, list) or len(embedding) != dimensions:
            raise BackfillValidationError(
                f"Embedding index {item_index} must have {dimensions} dimensions"
            )
        vector: list[float] = []
        for dim, value in enumerate(embedding):
            number = float(value)
            if not math.isfinite(number):
                raise BackfillValidationError(f"Embedding index {item_index} dimension {dim} is not finite")
            vector.append(number)
        ordered[item_index] = vector

    if any(vector is None for vector in ordered):
        raise BackfillValidationError("Missing one or more embedding indexes")
    return [vector for vector in ordered if vector is not None]


def vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(format(value, ".9g") for value in embedding) + "]"


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_payload(chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> list[dict[str, Any]]:
    return [
        {
            "id": chunk["id"],
            "document_id": chunk["document_id"],
            "document_code": chunk["document_code"],
            "document_version": chunk["document_version"],
            "language_code": chunk["language_code"],
            "chunk_index": chunk["chunk_index"],
            "embedding": vector_literal(embedding),
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]


def build_sql(payload: list[dict[str, Any]], model: str, dimensions: int) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    documents: dict[tuple[str | None, str, str, str | None], list[int]] = defaultdict(list)
    for row in payload:
        key = (
            row["document_id"],
            row["document_code"],
            row["document_version"],
            row["language_code"],
        )
        documents[key].append(int(row["chunk_index"]))

    audit_selects: list[str] = []
    for (document_id, code, version, language), indexes in sorted(documents.items(), key=lambda item: item[0][1:3]):
        details = {
            "run": "R06-A02",
            "operation": "embedding_backfill",
            "chunk_count": len(indexes),
            "chunk_indexes": sorted(indexes),
            "embedding_dimensions": dimensions,
            "retrieval_gate": "hybrid_search_v3 CRAVE-029 fail-closed",
        }
        audit_selects.append(
            "select public.write_audit_log("
            "null::uuid,"
            "'codex-r06-a02'::text,"
            "'system'::text,"
            "'document_index'::public.audit_action,"
            f"{sql_quote('R06-A02 embedding backfill: ' + code + ' ' + version)}::text,"
            "null::text,"
            "null::text[],"
            f"{sql_quote(document_id) + '::uuid' if document_id else 'null::uuid'},"
            f"{sql_quote(code)}::text,"
            f"{sql_quote(version)}::text,"
            f"{sql_quote(language)}::public.language_code" if language else "null::public.language_code,"
            "null::text,"
            f"{sql_quote(model)}::text,"
            "null::text,"
            "null::text,"
            "null::text,"
            "'R06-A02'::text,"
            f"{sql_quote(json.dumps(details, ensure_ascii=False, separators=(',', ':')))}::jsonb,"
            "null::text"
            ");"
        )

    return f"""begin;

with payload as (
  select *
  from jsonb_to_recordset({sql_quote(payload_json)}::jsonb) as x(
    id uuid,
    document_id uuid,
    document_code text,
    document_version text,
    language_code text,
    chunk_index integer,
    embedding text
  )
),
updated as (
  update public.document_chunks dc
     set embedding = payload.embedding::extensions.vector,
         updated_at = now()
    from payload
   where dc.id = payload.id
     and dc.embedding is null
     and dc.status = 'approved_for_ai_use'::public.document_status
  returning dc.id
)
select
  (select count(*) from payload) as expected_updates,
  (select count(*) from updated) as actual_updates;

{chr(10).join(audit_selects)}

commit;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and build CRAVE R06 embedding backfill SQL")
    parser.add_argument("--chunks-json", required=True, type=Path)
    parser.add_argument("--embeddings-json", type=Path)
    parser.add_argument("--expected-count", type=int, default=DEFAULT_EXPECTED_COUNT)
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-sql", type=Path)
    args = parser.parse_args()

    chunks = validate_chunks(as_rows(load_json(args.chunks_json)), args.expected_count)
    if args.embeddings_json is None:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_CHUNKS_ONLY",
                    "chunks": len(chunks),
                    "model": args.model,
                    "dimensions": args.dimensions,
                    "documents": sorted({row["document_code"] for row in chunks}),
                },
                ensure_ascii=False,
            )
        )
        return 0

    response = load_json(args.embeddings_json)
    embeddings = validate_embeddings(response, args.expected_count, args.dimensions)
    sql = build_sql(build_payload(chunks, embeddings), args.model, args.dimensions)
    if args.output_sql:
        args.output_sql.write_text(sql, encoding="utf-8")
    else:
        print(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
