#!/usr/bin/env python3
"""Build the R05-A41 live-only workflow source from the reviewed R05-A40 source."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/r05_a40_controlled_agent_canary_workflow.js"
TARGET = ROOT / "work/r05_a41_controlled_agent_canary_live_workflow.js"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    workflow = SOURCE.read_text(encoding="utf-8")
    workflow = workflow.replace("R05-A40-source-v1", "R05-A41-live-v1")

    gate_cte = (
        "\"), gate_question AS (\" + '\\n' +\n"
        "  \"  SELECT mapping.case_id, mapping.gate_name, question.id AS question_id\" + '\\n' +\n"
        "  \"  FROM (VALUES\" + '\\n' +\n"
        "  \"    ('U10-001', 'U10', 'R05-A41-U10'),\" + '\\n' +\n"
        "  \"    ('U11-001', 'U11', 'R05-A41-U11'),\" + '\\n' +\n"
        "  \"    ('U13-001', 'U13', 'R05-A41-U13'),\" + '\\n' +\n"
        "  \"    ('U14-001', 'U14', 'R05-A41-U14'),\" + '\\n' +\n"
        "  \"    ('U15-001', 'U15', 'R05-A41-U15')\" + '\\n' +\n"
        "  \"  ) AS mapping(case_id, gate_name, category)\" + '\\n' +\n"
        "  \"  JOIN LATERAL (\" + '\\n' +\n"
        "  \"    SELECT id\" + '\\n' +\n"
        "  \"    FROM public.golden_questions\" + '\\n' +\n"
        "  \"    WHERE category = mapping.category AND is_active = true\" + '\\n' +\n"
        "  \"    ORDER BY created_at DESC, id DESC\" + '\\n' +\n"
        "  \"    LIMIT 1\" + '\\n' +\n"
        "  \"  ) question ON true\" + '\\n' +\n"
        "\"), eval_result AS (\" + '\\n' +"
    )
    workflow = replace_once(
        workflow,
        "\"), eval_result AS (\" + '\\n' +",
        gate_cte,
        "insert gate_question CTE",
    )
    workflow = replace_once(
        workflow,
        "\"    eval_run.id, NULL::uuid, 'R05-A40-CONTROLLED-CANARY', 1, CASE WHEN $12::boolean THEN 1 ELSE NULL END,\" + '\\n' +",
        "\"    eval_run.id, gate.question_id, 'R05-A40-CONTROLLED-CANARY', 1, CASE WHEN $12::boolean THEN 1 ELSE NULL END,\" + '\\n' +",
        "bind eval result question id",
    )
    workflow = replace_once(
        workflow,
        (
            "\"  FROM eval_run CROSS JOIN retrieval_row CROSS JOIN query_row\" + '\\n' +\n"
            "  \"  CROSS JOIN (VALUES\" + '\\n' +\n"
            "  \"    ('U10-001', 'U10'),\" + '\\n' +\n"
            "  \"    ('U11-001', 'U11'),\" + '\\n' +\n"
            "  \"    ('U13-001', 'U13'),\" + '\\n' +\n"
            "  \"    ('U14-001', 'U14'),\" + '\\n' +\n"
            "  \"    ('U15-001', 'U15')\" + '\\n' +\n"
            "  \"  ) AS gate(case_id, gate_name)\" + '\\n' +"
        ),
        (
            "\"  FROM eval_run CROSS JOIN retrieval_row CROSS JOIN query_row\" + '\\n' +\n"
            "  \"  CROSS JOIN gate_question gate\" + '\\n' +"
        ),
        "replace inline gate values",
    )

    workflow = workflow.replace(
        "          { name: 'apikey', value: '__REDACTED_SUPABASE_ANON_KEY__' },\n",
        "",
    )
    if "__REDACTED_SUPABASE_ANON_KEY__" in workflow:
        raise RuntimeError("static Supabase placeholder remained in live source")

    workflow = replace_once(
        workflow,
        (
            "      url: 'https://bdttccztjtrcaztjgkot.supabase.co/auth/v1/user',\n"
            "      sendHeaders: true,"
        ),
        (
            "      url: 'https://bdttccztjtrcaztjgkot.supabase.co/auth/v1/user',\n"
            "      authentication: 'genericCredentialType',\n"
            "      genericAuthType: 'httpHeaderAuth',\n"
            "      sendHeaders: true,"
        ),
        "configure Verify JWT credential mode",
    )
    workflow = replace_once(
        workflow,
        (
            "    },\n"
            "  },\n"
            "  output: [{ id: '00000000-0000-4000-8000-000000000000', email: 'qa@example.invalid' }],"
        ),
        (
            "    },\n"
            "    credentials: { httpHeaderAuth: newCredential('x-api-key') },\n"
            "  },\n"
            "  output: [{ id: '00000000-0000-4000-8000-000000000000', email: 'qa@example.invalid' }],"
        ),
        "bind Verify JWT x-api-key",
    )
    workflow = replace_once(
        workflow,
        (
            "      url: 'https://bdttccztjtrcaztjgkot.supabase.co/rest/v1/rpc/hybrid_search_v3',\n"
            "      sendHeaders: true,"
        ),
        (
            "      url: 'https://bdttccztjtrcaztjgkot.supabase.co/rest/v1/rpc/hybrid_search_v3',\n"
            "      authentication: 'genericCredentialType',\n"
            "      genericAuthType: 'httpHeaderAuth',\n"
            "      sendHeaders: true,"
        ),
        "configure Hybrid Search credential mode",
    )
    workflow = replace_once(
        workflow,
        (
            "    },\n"
            "  },\n"
            "  output: [{\n"
            "    chunk_id: '00000000-0000-4000-8000-000000000001',"
        ),
        (
            "    },\n"
            "    credentials: { httpHeaderAuth: newCredential('x-api-key') },\n"
            "  },\n"
            "  output: [{\n"
            "    chunk_id: '00000000-0000-4000-8000-000000000001',"
        ),
        "bind Hybrid Search x-api-key",
    )
    workflow = replace_once(
        workflow,
        (
            "'R05-A40 source-only. Do not create/update/execute/publish this workflow without a separate A41 approval. "
            "Retrieval path is Supabase RPC with caller user JWT; Postgres is used only to persist controlled evidence.'"
        ),
        (
            "'R05-A41 approved controlled live canary. Keep inactive/unpublished; use caller JWT plus x-api-key for "
            "Supabase HTTP and GMP-check only for append-only controlled evidence. Archive after the bounded run.'"
        ),
        "replace scope note",
    )

    TARGET.write_text(workflow, encoding="utf-8")
    print(TARGET.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
