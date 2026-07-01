#!/usr/bin/env python3
"""Create, retain, and retire the R05-A42 synthetic controlled-canary identity.

The operator never prints Supabase project keys, passwords, or refresh tokens.
The short-lived access token is written only to a mode-0600 runtime file and can
be emitted explicitly with the ``token`` subcommand for the one bounded n8n run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
PROJECT_REF = "bdttccztjtrcaztjgkot"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"
ADMIN_PROFILE_ID = uuid.UUID("08d0572c-9368-4034-bb26-ab1c88bd9e04")
QA_MANAGER_ROLE_ID = uuid.UUID("c6b1d532-4df4-4fa8-b4d7-0ea46c8fd071")
SEED_CHUNK_ID = uuid.UUID("13cecde7-5a35-4f08-970b-9896fd1085a5")
# Reuse the immutable five-case artifact; the live dataset identity/version below
# is A42-specific so retained A41 rows are never overwritten or reactivated.
DATASET_PATH = "eval/datasets/r05_a40_agent_canary_u10_u15.jsonl"
DATASET_SHA256 = "a93bf04f4ce42c47827c427ebb41d8a2d18bdff411df6ed5a87f93aef6147e94"
WORKFLOW_NAME = "TKTL R05-A42 Controlled Agent Canary"
WORKFLOW_VERSION = "R05-A42-live-v1"
RELEASE_CANDIDATE = "r05-a42-rc1"
SYNTHETIC_CONTENT = (
    "R05-A42 synthetic controlled canary. Thiết bị đo lường GMP phải được hiệu chuẩn "
    "theo lịch, có nhãn trạng thái và hồ sơ truy xuất. Đây là dữ liệu tổng hợp chỉ "
    "dùng kiểm thử; không phải hướng dẫn sản xuất."
)


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=True, cwd=ROOT)


def load_project_keys() -> tuple[str, str]:
    completed = run_cli(
        [
            "supabase",
            "projects",
            "api-keys",
            "--project-ref",
            PROJECT_REF,
            "--reveal",
            "--output",
            "json",
        ]
    )
    payload = json.loads(completed.stdout)
    service = next(
        (item.get("api_key") for item in payload if item.get("name") == "service_role"),
        None,
    )
    anon = next(
        (item.get("api_key") for item in payload if item.get("name") == "anon"),
        None,
    )
    if not service or not anon:
        raise RuntimeError("Không tìm thấy service_role/anon key; dừng fail-closed.")
    return service, anon


def request_json(
    method: str,
    url: str,
    apikey: str,
    body: Optional[dict[str, Any]] = None,
) -> Any:
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=raw,
        method=method,
        headers={
            "apikey": apikey,
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8")
        raise RuntimeError(
            f"Supabase Auth HTTP {error.code}: {response_body[:500]}"
        ) from error
    return json.loads(response_body) if response_body else {}


def create_user(service_key: str, email: str, password: str) -> str:
    payload = request_json(
        "POST",
        f"{SUPABASE_URL}/auth/v1/admin/users",
        service_key,
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "crave_canary": "r05_a42_blk007",
                "canary_state": "active_short_lived",
                "retained_identity": True,
                "hard_delete_identity_allowed": False,
            },
        },
    )
    user_id = payload.get("id") or (payload.get("user") or {}).get("id")
    if not isinstance(user_id, str) or not user_id:
        raise RuntimeError("Admin create user không trả actor id hợp lệ.")
    uuid.UUID(user_id)
    return user_id


def sign_in(anon_key: str, email: str, password: str) -> Tuple[str, Optional[int]]:
    payload = request_json(
        "POST",
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        anon_key,
        {"email": email, "password": password},
    )
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Password sign-in không trả access token.")
    expires_in = payload.get("expires_in")
    return token, expires_in if isinstance(expires_in, int) else None


def ban_user(service_key: str, user_id: str) -> dict[str, Any]:
    payload = request_json(
        "PUT",
        f"{SUPABASE_URL}/auth/v1/admin/users/{urllib.parse.quote(user_id)}",
        service_key,
        {
            "ban_duration": "876000h",
            "user_metadata": {
                "crave_canary": "r05_a42_blk007",
                "canary_state": "retired_banned",
                "retained_identity": True,
                "hard_delete_identity_allowed": False,
            },
        },
    )
    user = payload.get("user") if isinstance(payload.get("user"), dict) else payload
    banned_until = user.get("banned_until") if isinstance(user, dict) else None
    if not banned_until:
        raise RuntimeError("Auth update không xác nhận banned_until; dừng fail-closed.")
    return {
        "actor_id": user_id,
        "banned_until": banned_until,
        "retained_identity": True,
        "hard_deleted": False,
    }


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def validate_runtime_path(path: Path) -> None:
    if path.suffix != ".json":
        raise RuntimeError("Runtime file phải có đuôi .json.")
    if not str(path.resolve()).startswith(("/private/tmp/", "/tmp/")):
        raise RuntimeError("Runtime file phải nằm trong /private/tmp hoặc /tmp.")


def write_secure_json(path: Path, payload: dict[str, Any]) -> None:
    validate_runtime_path(path)
    if path.exists():
        raise RuntimeError(f"Runtime file đã tồn tại: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def rewrite_secure_json(path: Path, payload: dict[str, Any]) -> None:
    validate_runtime_path(path)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def fixture_ids() -> dict[str, Any]:
    return {
        "user_role_id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4()),
        "raw_file_id": str(uuid.uuid4()),
        "document_version_id": str(uuid.uuid4()),
        "document_chunk_id": str(uuid.uuid4()),
        "document_access_id": str(uuid.uuid4()),
        "retrieval_profile_id": str(uuid.uuid4()),
        "eval_dataset_id": str(uuid.uuid4()),
        "golden_question_ids": {
            gate: str(uuid.uuid4())
            for gate in ("U10", "U11", "U13", "U14", "U15")
        },
    }


def seed_sql(actor_id: str, email: str, ids: dict[str, Any], git_commit: str) -> str:
    document_code = "R05-A42-CANARY"
    version_label = "r05-a42-v1"
    drive_file_id = f"r05-a42-synthetic-{actor_id}"
    binary_sha = hashlib.sha256(
        b"CRAVE-R05-A42-SYNTHETIC-RAW-FILE-V1"
    ).hexdigest()
    content_sha = hashlib.sha256(SYNTHETIC_CONTENT.encode("utf-8")).hexdigest()
    question_values = []
    for gate, question_id in ids["golden_question_ids"].items():
        question_values.append(
            "("
            f"'{question_id}'::uuid, "
            f"{sql_string(f'R05-A42 {gate}: xác minh controlled canary có nguồn và citation [1].')}, "
            f"{sql_string('DRAFT synthetic answer phải dựa trên R05-A42-CANARY và có citation [1].')}, "
            f"ARRAY[{sql_string(document_code)}]::text[], "
            "'HIGH'::public.confidence_level, 'vi'::public.language_code, "
            f"{sql_string(f'R05-A42-{gate}')}, 'medium', true, '{actor_id}'::uuid"
            ")"
        )
    questions_sql = ",\n  ".join(question_values)
    return f"""-- R05-A42 expanded controlled-canary fixture.
-- LIVE WRITE: approved by the user for project {PROJECT_REF}.
-- Retained synthetic evidence; no production publication.

begin;

do $preflight$
begin
  if not exists (
    select 1 from auth.users
    where id = '{actor_id}'::uuid
      and lower(email) = lower({sql_string(email)})
      and raw_user_meta_data->>'crave_canary' = 'r05_a42_blk007'
  ) then
    raise exception 'R05-A42 seed: Auth actor missing or marker mismatch.';
  end if;
  if exists (
    select 1 from public.user_profiles
    where id = '{actor_id}'::uuid or lower(email) = lower({sql_string(email)})
  ) then
    raise exception 'R05-A42 seed: profile residue already exists.';
  end if;
  if not exists (
    select 1 from public.user_profiles
    where id = '{ADMIN_PROFILE_ID}'::uuid and is_active = true
  ) then
    raise exception 'R05-A42 seed: active approving admin profile missing.';
  end if;
  if not exists (
    select 1 from public.roles
    where id = '{QA_MANAGER_ROLE_ID}'::uuid
      and role_name = 'qa_manager'::public.user_role_name
  ) then
    raise exception 'R05-A42 seed: qa_manager role missing.';
  end if;
  if not exists (
    select 1 from public.document_chunks
    where id = '{SEED_CHUNK_ID}'::uuid
      and embedding is not null
      and vector_dims(embedding) = 1536
  ) then
    raise exception 'R05-A42 seed: 1536-d seed embedding missing.';
  end if;
  if exists (
    select 1 from public.documents
    where document_code = '{document_code}'
      and version = '{version_label}'
      and language_code = 'vi'::public.language_code
  ) or exists (
    select 1 from public.raw_files where drive_file_id = {sql_string(drive_file_id)}
  ) or exists (
    select 1 from public.retrieval_profiles
    where profile_name = 'r05_a42_controlled_agent_canary'
      and profile_version = 'r05-a42-v1'
  ) or exists (
    select 1 from public.eval_datasets
    where dataset_name = 'r05_a42_agent_canary_u10_u15'
      and dataset_version = 'r05-a42-v1'
  ) or exists (
    select 1 from public.golden_questions
    where category in ('R05-A42-U10','R05-A42-U11','R05-A42-U13','R05-A42-U14','R05-A42-U15')
      and is_active = true
  ) then
    raise exception 'R05-A42 seed: active fixture residue already exists.';
  end if;
end
$preflight$;

insert into public.user_profiles (
  id, full_name, email, department, position, employee_code,
  is_active, preferred_language
) values (
  '{actor_id}'::uuid,
  'CRAVE R05-A42 Retained Synthetic Canary',
  {sql_string(email)},
  'QA-CANARY',
  'Temporary controlled canary actor',
  'R05-A42-CANARY',
  true,
  'vi'::public.language_code
);

insert into public.user_roles (
  id, user_id, role_id, granted_by, granted_at, is_active
) values (
  '{ids["user_role_id"]}'::uuid,
  '{actor_id}'::uuid,
  '{QA_MANAGER_ROLE_ID}'::uuid,
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  true
);

insert into public.documents (
  id, document_group_id, document_code, document_title, document_type,
  language_code, source_language, source_type, version, effective_date,
  status, approved_for_ai_use, source_priority, owner_department, access_level,
  file_name, file_path, file_size_bytes, file_hash, mime_type,
  page_count, chunk_count, uploaded_by, uploaded_at, indexed_at,
  reviewed_by, reviewed_at, approved_by, approved_at,
  source_category, trust_level, source_organization,
  last_verified_at, next_review_date, lifecycle_note
) values (
  '{ids["document_id"]}'::uuid,
  'R05-A42-SYNTHETIC-CANARY',
  '{document_code}',
  'R05-A42 Retained Synthetic Controlled Agent Canary',
  'guideline'::public.document_type,
  'vi'::public.language_code,
  'vi',
  'guideline'::public.source_type,
  '{version_label}',
  current_date,
  'approved_for_ai_use'::public.document_status,
  true,
  1,
  'QA-CANARY',
  'restricted-canary',
  'r05_a42_synthetic_canary.txt',
  'synthetic/r05-a42/r05_a42_synthetic_canary.txt',
  {len(SYNTHETIC_CONTENT.encode("utf-8"))},
  '{binary_sha}',
  'text/plain',
  1,
  1,
  '{actor_id}'::uuid,
  clock_timestamp(),
  clock_timestamp(),
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  'synthetic_canary',
  1,
  'CRAVE QA',
  clock_timestamp(),
  current_date + 1,
  'R05-A42 bounded synthetic canary; archive and deny AI immediately after verification.'
);

insert into public.raw_files (
  id, document_id, drive_file_id, file_name, mime_type, file_size_bytes,
  binary_sha256, hash_status, status, storage_provider, storage_path_hint,
  stored_by, stored_at, verified_at
) values (
  '{ids["raw_file_id"]}'::uuid,
  '{ids["document_id"]}'::uuid,
  {sql_string(drive_file_id)},
  'r05_a42_synthetic_canary.txt',
  'text/plain',
  {len(SYNTHETIC_CONTENT.encode("utf-8"))},
  '{binary_sha}',
  'verified',
  'verified',
  'controlled_upload',
  'synthetic/r05-a42/r05_a42_synthetic_canary.txt',
  '{actor_id}'::uuid,
  clock_timestamp(),
  clock_timestamp()
);

insert into public.document_versions (
  id, document_id, raw_file_id, version_label, record_origin,
  source_document_id, source_url, source_updated_at, effective_date,
  drive_file_id, binary_sha256, content_sha256, hash_status, license_status,
  parse_status, parse_quality_score, parse_engine, parse_engine_version,
  parsed_at, parse_reviewed_by, parse_reviewed_at,
  approval_evidence_status, approved_for_ai_use, approved_by, approved_at,
  index_status, index_version
) values (
  '{ids["document_version_id"]}'::uuid,
  '{ids["document_id"]}'::uuid,
  '{ids["raw_file_id"]}'::uuid,
  '{version_label}',
  'ingest',
  {sql_string(drive_file_id)},
  {sql_string(f'urn:crave:synthetic:r05-a42:{actor_id}')},
  clock_timestamp(),
  current_date,
  {sql_string(drive_file_id)},
  '{binary_sha}',
  '{content_sha}',
  'verified',
  'curated',
  'success',
  100,
  'controlled-synthetic-fixture',
  'r05-a42-v1',
  clock_timestamp(),
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  'verified',
  true,
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  'ready',
  'r05-a42-v1'
);

update public.documents
set current_version_id = '{ids["document_version_id"]}'::uuid,
    updated_at = clock_timestamp()
where id = '{ids["document_id"]}'::uuid;

insert into public.document_chunks (
  id, document_id, content, content_tokens, chunk_index, page_number,
  section_code, section_title, chunk_type, document_code, document_version,
  language_code, source_type, file_hash, embedding, status, source_priority,
  source_category, trust_level, source_organization, is_summary,
  quality_score, document_version_id
)
select
  '{ids["document_chunk_id"]}'::uuid,
  '{ids["document_id"]}'::uuid,
  {sql_string(SYNTHETIC_CONTENT)},
  null,
  0,
  1,
  'CANARY',
  'Controlled synthetic calibration canary',
  'text',
  '{document_code}',
  '{version_label}',
  'vi'::public.language_code,
  'guideline'::public.source_type,
  '{binary_sha}',
  seed.embedding,
  'approved_for_ai_use'::public.document_status,
  1,
  'synthetic_canary',
  1,
  'CRAVE QA',
  false,
  1.0,
  '{ids["document_version_id"]}'::uuid
from public.document_chunks seed
where seed.id = '{SEED_CHUNK_ID}'::uuid;

insert into public.document_access (
  id, document_id, user_id, role_name, department,
  can_view, can_edit, can_approve, granted_by, granted_at, expires_at, is_active
) values (
  '{ids["document_access_id"]}'::uuid,
  '{ids["document_id"]}'::uuid,
  '{actor_id}'::uuid,
  'qa_manager'::public.user_role_name,
  'QA-CANARY',
  true,
  false,
  false,
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  clock_timestamp() + interval '30 minutes',
  true
);

insert into public.golden_questions (
  id, question_text, expected_answer, expected_sources, expected_confidence,
  question_language, category, difficulty, is_active, created_by
) values
  {questions_sql};

insert into public.retrieval_profiles (
  id, profile_name, profile_version, embedding_model, embedding_dimensions,
  fts_pool_size, vector_pool_size, final_top_k, rrf_k, score_threshold,
  weights, status, git_commit, approved_by, approved_at, valid_from, expires_at
) values (
  '{ids["retrieval_profile_id"]}'::uuid,
  'r05_a42_controlled_agent_canary',
  'r05-a42-v1',
  'text-embedding-3-small',
  1536,
  20,
  20,
  3,
  60,
  0.4,
  '{{"fts":0.22,"vector":0.55,"metadata":0.23}}'::jsonb,
  'approved',
  '{git_commit}',
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  clock_timestamp(),
  clock_timestamp() + interval '2 hours'
);

insert into public.eval_datasets (
  id, dataset_name, dataset_version, artifact_path, artifact_sha256,
  question_count, status, created_by, approved_by, approved_at, valid_from, expires_at
) values (
  '{ids["eval_dataset_id"]}'::uuid,
  'r05_a42_agent_canary_u10_u15',
  'r05-a42-v1',
  '{DATASET_PATH}',
  '{DATASET_SHA256}',
  5,
  'approved',
  '{actor_id}'::uuid,
  '{ADMIN_PROFILE_ID}'::uuid,
  clock_timestamp(),
  clock_timestamp(),
  clock_timestamp() + interval '2 hours'
);

insert into public.audit_log (
  user_id, user_email, user_role, action_type, input_summary,
  document_id, document_code, document_version, language_code,
  file_hash, session_id, details
) values
(
  '{ADMIN_PROFILE_ID}'::uuid,
  'tienhoan.dhd@gmail.com',
  'admin',
  'user_create'::public.audit_action,
  'Create retained short-lived R05-A42 synthetic canary actor profile.',
  null,
  null,
  null,
  'vi'::public.language_code,
  null,
  'R05-A42',
  jsonb_build_object('actor_id','{actor_id}','retained_identity',true,'hard_delete_allowed',false)
),
(
  '{ADMIN_PROFILE_ID}'::uuid,
  'tienhoan.dhd@gmail.com',
  'admin',
  'access_grant'::public.audit_action,
  'Grant bounded direct view access and temporary qa_manager role for R05-A42.',
  '{ids["document_id"]}'::uuid,
  '{document_code}',
  '{version_label}',
  'vi'::public.language_code,
  '{binary_sha}',
  'R05-A42',
  jsonb_build_object('access_id','{ids["document_access_id"]}','role_assignment_id','{ids["user_role_id"]}','expires_in_minutes',30)
),
(
  '{actor_id}'::uuid,
  {sql_string(email)},
  'qa_manager',
  'document_upload'::public.audit_action,
  'Create retained synthetic current-version canary fixture with copied 1536-d seed embedding.',
  '{ids["document_id"]}'::uuid,
  '{document_code}',
  '{version_label}',
  'vi'::public.language_code,
  '{binary_sha}',
  'R05-A42',
  jsonb_build_object('raw_file_id','{ids["raw_file_id"]}','document_version_id','{ids["document_version_id"]}','chunk_id','{ids["document_chunk_id"]}','seed_chunk_id','{SEED_CHUNK_ID}')
),
(
  '{ADMIN_PROFILE_ID}'::uuid,
  'tienhoan.dhd@gmail.com',
  'admin',
  'config_change'::public.audit_action,
  'Approve bounded retrieval profile and U10/U11/U13/U14/U15 eval dataset for R05-A42.',
  '{ids["document_id"]}'::uuid,
  '{document_code}',
  '{version_label}',
  'vi'::public.language_code,
  '{binary_sha}',
  'R05-A42',
  jsonb_build_object('retrieval_profile_id','{ids["retrieval_profile_id"]}','eval_dataset_id','{ids["eval_dataset_id"]}','git_commit','{git_commit}')
);

commit;
"""


def verify_fixture_sql(actor_id: str, ids: dict[str, Any]) -> str:
    return f"""-- R05-A42 live fixture verification.
-- READ-ONLY.

select jsonb_pretty(jsonb_build_object(
  'auth_actor', (
    select jsonb_build_object(
      'exists', count(*) = 1,
      'confirmed', bool_and(email_confirmed_at is not null),
      'not_banned', bool_and(banned_until is null or banned_until <= clock_timestamp())
    )
    from auth.users where id = '{actor_id}'::uuid
  ),
  'profile_active', (
    select count(*) = 1 from public.user_profiles
    where id = '{actor_id}'::uuid and is_active = true
  ),
  'qa_manager_role_active', (
    select count(*) = 1 from public.user_roles
    where id = '{ids["user_role_id"]}'::uuid
      and user_id = '{actor_id}'::uuid and is_active = true
  ),
  'direct_access_active', (
    select count(*) = 1 from public.document_access
    where id = '{ids["document_access_id"]}'::uuid
      and user_id = '{actor_id}'::uuid
      and can_view = true and is_active = true
      and expires_at > clock_timestamp()
  ),
  'document_current_and_approved', (
    select count(*) = 1 from public.documents
    where id = '{ids["document_id"]}'::uuid
      and current_version_id = '{ids["document_version_id"]}'::uuid
      and status = 'approved_for_ai_use'::public.document_status
      and approved_for_ai_use = true
  ),
  'raw_file_verified', (
    select count(*) = 1 from public.raw_files
    where id = '{ids["raw_file_id"]}'::uuid
      and status = 'verified' and hash_status = 'verified'
      and binary_sha256 is not null and verified_at is not null
  ),
  'version_eligible', (
    select count(*) = 1 from public.document_versions
    where id = '{ids["document_version_id"]}'::uuid
      and approved_for_ai_use = true
      and approval_evidence_status = 'verified'
      and hash_status = 'verified'
      and license_status = 'curated'
      and parse_status = 'success'
      and index_status = 'ready'
      and retired_at is null
  ),
  'chunk_1536_approved', (
    select count(*) = 1 from public.document_chunks
    where id = '{ids["document_chunk_id"]}'::uuid
      and document_version_id = '{ids["document_version_id"]}'::uuid
      and status = 'approved_for_ai_use'::public.document_status
      and vector_dims(embedding) = 1536
  ),
  'golden_questions_active', (
    select count(*) from public.golden_questions
    where id in (
      '{ids["golden_question_ids"]["U10"]}'::uuid,
      '{ids["golden_question_ids"]["U11"]}'::uuid,
      '{ids["golden_question_ids"]["U13"]}'::uuid,
      '{ids["golden_question_ids"]["U14"]}'::uuid,
      '{ids["golden_question_ids"]["U15"]}'::uuid
    ) and is_active = true
  ),
  'retrieval_profile_approved', (
    select count(*) = 1 from public.retrieval_profiles
    where id = '{ids["retrieval_profile_id"]}'::uuid
      and status = 'approved' and valid_from <= clock_timestamp()
      and expires_at > clock_timestamp()
  ),
  'eval_dataset_approved', (
    select count(*) = 1 from public.eval_datasets
    where id = '{ids["eval_dataset_id"]}'::uuid
      and status = 'approved' and question_count = 5
      and valid_from <= clock_timestamp() and expires_at > clock_timestamp()
  ),
  'hybrid_search_fixture_hits', (
    select count(*) from public.hybrid_search_v3(
      (select embedding from public.document_chunks where id = '{ids["document_chunk_id"]}'::uuid),
      'hiệu chuẩn thiết bị đo lường GMP',
      0.4,
      3,
      '{actor_id}'::uuid,
      'any',
      'any',
      null,
      5,
      null,
      0.3
    ) result
    where result.document_id = '{ids["document_id"]}'::uuid
      and result.chunk_id = '{ids["document_chunk_id"]}'::uuid
  ),
  'seed_audit_rows', (
    select count(*) from public.audit_log
    where session_id = 'R05-A42'
      and details @> jsonb_build_object('actor_id','{actor_id}') = true
       or (
         session_id = 'R05-A42'
         and document_id = '{ids["document_id"]}'::uuid
       )
  )
)) as fixture_verification;
"""


def verify_evidence_sql(actor_id: str, ids: dict[str, Any], git_commit: str) -> str:
    return f"""-- R05-A42 controlled-canary evidence verification.
-- READ-ONLY.

with target_run as (
  select id
  from public.eval_runs
  where workflow_name = '{WORKFLOW_NAME}'
    and workflow_version = '{WORKFLOW_VERSION}'
    and git_commit_sha = '{git_commit}'
    and release_candidate = '{RELEASE_CANDIDATE}'
  order by completed_at desc nulls last, started_at desc nulls last, id desc
  limit 1
),
target_query as (
  select id
  from public.ai_queries
  where user_id = '{actor_id}'::uuid
    and filters @> '{{"canary":true}}'::jsonb
  order by created_at desc nulls last, id desc
  limit 1
),
target_retrieval as (
  select id
  from public.retrieval_log
  where query_id = (select id from target_query)
  order by created_at desc nulls last, id desc
  limit 1
)
select jsonb_pretty(jsonb_build_object(
  'eval_run_id', (select id from target_run),
  'eval_run_count', (select count(*) from target_run),
  'eval_run_passed', (
    select count(*) = 1 from public.eval_runs
    where id = (select id from target_run)
      and eval_contract_version = 'v2'
      and run_status = 'passed'
      and passed = true
      and n_questions = 5
  ),
  'eval_result_count', (
    select count(*) from public.eval_results
    where run_id = (select id from target_run)
  ),
  'eval_result_pass_count', (
    select count(*) from public.eval_results
    where run_id = (select id from target_run)
      and passed = true
      and permission_leakage_count = 0
      and stale_version_count = 0
      and permission_pass = true
      and version_freshness_pass = true
      and tool_policy_pass = true
      and citation_grounding_score = 1
  ),
  'eval_failure_count', (
    select count(*)
    from public.eval_failures failure
    join public.eval_results result on result.id = failure.eval_result_id
    where result.run_id = (select id from target_run)
  ),
  'eval_gate', (
    select case
      when (select id from target_run) is null then null
      else public.crave_evaluate_eval_v2_release_gate_v1((select id from target_run))
    end
  ),
  'health_gate', public.crave_evaluate_system_health_gate_v1(
    array[
      'crave.agent.canary.jwt_boundary',
      'crave.agent.canary.retrieval_logged',
      'crave.agent.canary.citation_grounded',
      'crave.agent.canary.tool_policy'
    ],
    interval '30 minutes'
  ),
  'agent_session_count', (
    select count(*) from public.agent_sessions
    where user_id = '{actor_id}'::uuid
      and workflow_name = '{WORKFLOW_NAME}'
      and workflow_version = '{WORKFLOW_VERSION}'
      and metadata->>'release_candidate' = '{RELEASE_CANDIDATE}'
  ),
  'ai_query_count', (select count(*) from target_query),
  'retrieval_log_count', (select count(*) from target_retrieval),
  'synthetic_candidate_count', (
    select count(*) from public.retrieval_candidates
    where retrieval_log_id = (select id from target_retrieval)
      and chunk_id = '{ids["document_chunk_id"]}'::uuid
      and document_version_id = '{ids["document_version_id"]}'::uuid
      and selected = true
  ),
  'grounded_citation_count', (
    select count(*) from public.ai_query_sources
    where query_id = (select id from target_query)
      and chunk_id = '{ids["document_chunk_id"]}'::uuid
      and document_version_id = '{ids["document_version_id"]}'::uuid
      and grounded = true
  ),
  'tool_call_count', (
    select count(*) from public.tool_call_log
    where user_id = '{actor_id}'::uuid
      and workflow_name = '{WORKFLOW_NAME}'
      and workflow_version = '{WORKFLOW_VERSION}'
  ),
  'healthy_metric_count', (
    select count(*) from public.system_health_metrics
    where source_name = 'R05-A42-controlled-canary'
      and labels->>'release_candidate' = '{RELEASE_CANDIDATE}'
      and status = 'healthy'
      and measured_at >= clock_timestamp() - interval '30 minutes'
  )
)) as evidence_verification;
"""


def retire_sql(actor_id: str, email: str, ids: dict[str, Any]) -> str:
    question_ids = ",\n    ".join(
        f"'{question_id}'::uuid"
        for question_id in ids["golden_question_ids"].values()
    )
    return f"""-- R05-A42 retained fixture retirement.
-- LIVE WRITE: deactivate/retire only; do not delete retained evidence.

begin;

insert into public.audit_log (
  user_id, user_email, user_role, action_type, input_summary,
  document_id, document_code, document_version, language_code,
  session_id, details
) values
(
  '{ADMIN_PROFILE_ID}'::uuid,
  'tienhoan.dhd@gmail.com',
  'admin',
  'access_revoke'::public.audit_action,
  'Revoke R05-A42 canary direct access and temporary qa_manager role.',
  '{ids["document_id"]}'::uuid,
  'R05-A42-CANARY',
  'r05-a42-v1',
  'vi'::public.language_code,
  'R05-A42',
  jsonb_build_object('actor_id','{actor_id}','access_id','{ids["document_access_id"]}','role_assignment_id','{ids["user_role_id"]}')
),
(
  '{ADMIN_PROFILE_ID}'::uuid,
  'tienhoan.dhd@gmail.com',
  'admin',
  'document_archive'::public.audit_action,
  'Archive and deny AI use for retained R05-A42 synthetic document/version/chunk.',
  '{ids["document_id"]}'::uuid,
  'R05-A42-CANARY',
  'r05-a42-v1',
  'vi'::public.language_code,
  'R05-A42',
  jsonb_build_object('document_version_id','{ids["document_version_id"]}','chunk_id','{ids["document_chunk_id"]}','retained',true)
),
(
  '{ADMIN_PROFILE_ID}'::uuid,
  'tienhoan.dhd@gmail.com',
  'admin',
  'security_event'::public.audit_action,
  'Retain but ban R05-A42 Auth actor after controlled canary execution.',
  '{ids["document_id"]}'::uuid,
  'R05-A42-CANARY',
  'r05-a42-v1',
  'vi'::public.language_code,
  'R05-A42',
  jsonb_build_object('actor_id','{actor_id}','actor_email',{sql_string(email)},'retained_identity',true,'hard_delete_allowed',false)
);

update public.document_access
set can_view = false,
    can_edit = false,
    can_approve = false,
    expires_at = clock_timestamp(),
    is_active = false
where id = '{ids["document_access_id"]}'::uuid;

update public.user_roles
set is_active = false
where id = '{ids["user_role_id"]}'::uuid
  and user_id = '{actor_id}'::uuid;

update public.golden_questions
set is_active = false,
    last_run_at = clock_timestamp(),
    last_run_passed = false,
    last_run_details = jsonb_build_object(
      'release_candidate', '{RELEASE_CANDIDATE}',
      'retired_after_canary', true,
      'canary_passed', false,
      'failure_code', 'HYBRID_SEARCH_V3_EXECUTE_DENIED'
    ),
    updated_at = clock_timestamp()
where id in (
    {question_ids}
);

-- retrieval_profiles và eval_datasets là append-only theo 030b/030c.
-- Không UPDATE để giữ ALCOA+; hai record đã có expires_at hữu hạn 2 giờ.

update public.document_chunks
set status = 'archived'::public.document_status,
    updated_at = clock_timestamp()
where id = '{ids["document_chunk_id"]}'::uuid;

update public.document_versions
set retired_at = clock_timestamp(),
    index_status = 'excluded'
where id = '{ids["document_version_id"]}'::uuid;

update public.documents
set status = 'archived'::public.document_status,
    approved_for_ai_use = false,
    retired_date = current_date,
    lifecycle_note = lifecycle_note || ' Retired after bounded R05-A42 canary attempt.',
    updated_at = clock_timestamp()
where id = '{ids["document_id"]}'::uuid;

update public.user_profiles
set is_active = false,
    updated_at = clock_timestamp()
where id = '{actor_id}'::uuid;

commit;
"""


def post_retire_verify_sql(actor_id: str, ids: dict[str, Any]) -> str:
    return f"""-- R05-A42 post-retirement verification.
-- READ-ONLY.

with target_run as (
  select id
  from public.eval_runs
  where workflow_name = '{WORKFLOW_NAME}'
    and workflow_version = '{WORKFLOW_VERSION}'
    and release_candidate = '{RELEASE_CANDIDATE}'
  order by completed_at desc nulls last, started_at desc nulls last, id desc
  limit 1
)
select jsonb_pretty(jsonb_build_object(
  'auth_actor_retained_and_banned', (
    select count(*) = 1 and bool_and(banned_until > clock_timestamp())
    from auth.users where id = '{actor_id}'::uuid
  ),
  'profile_inactive', (
    select count(*) = 1 from public.user_profiles
    where id = '{actor_id}'::uuid and is_active = false
  ),
  'role_inactive', (
    select count(*) = 1 from public.user_roles
    where id = '{ids["user_role_id"]}'::uuid and is_active = false
  ),
  'access_inactive', (
    select count(*) = 1 from public.document_access
    where id = '{ids["document_access_id"]}'::uuid
      and is_active = false and can_view = false
      and can_edit = false and can_approve = false
      and expires_at <= clock_timestamp()
  ),
  'golden_questions_inactive', (
    select count(*) from public.golden_questions
    where category in ('R05-A42-U10','R05-A42-U11','R05-A42-U13','R05-A42-U14','R05-A42-U15')
      and is_active = false
  ),
  'retrieval_profile_append_only_bounded', (
    select count(*) = 1 from public.retrieval_profiles
    where id = '{ids["retrieval_profile_id"]}'::uuid
      and status = 'approved' and expires_at is not null
  ),
  'eval_dataset_append_only_bounded', (
    select count(*) = 1 from public.eval_datasets
    where id = '{ids["eval_dataset_id"]}'::uuid
      and status = 'approved' and expires_at is not null
  ),
  'document_archived_ai_denied', (
    select count(*) = 1 from public.documents
    where id = '{ids["document_id"]}'::uuid
      and status = 'archived'::public.document_status
      and approved_for_ai_use = false
      and retired_date is not null
  ),
  'version_retired_ai_denied', (
    select count(*) = 1 from public.document_versions
    where id = '{ids["document_version_id"]}'::uuid
      and retired_at is not null
      and index_status = 'excluded'
  ),
  'chunk_archived', (
    select count(*) = 1 from public.document_chunks
    where id = '{ids["document_chunk_id"]}'::uuid
      and status = 'archived'::public.document_status
      and vector_dims(embedding) = 1536
  ),
  'hybrid_search_fixture_hits_after_retire', (
    select count(*) from public.hybrid_search_v3(
      (select embedding from public.document_chunks where id = '{ids["document_chunk_id"]}'::uuid),
      'hiệu chuẩn thiết bị đo lường GMP',
      0.4,
      3,
      '{actor_id}'::uuid,
      'any',
      'any',
      null,
      5,
      null,
      0.3
    ) result
    where result.document_id = '{ids["document_id"]}'::uuid
  ),
  'retained_eval_run_count', (select count(*) from target_run),
  'retained_eval_result_count', (
    select count(*) from public.eval_results
    where run_id = (select id from target_run)
  ),
  'retained_grounded_citation_count', (
    select count(*) from public.ai_query_sources
    where chunk_id = '{ids["document_chunk_id"]}'::uuid
      and document_version_id = '{ids["document_version_id"]}'::uuid
      and grounded = true
  ),
  'retirement_audit_rows', (
    select count(*) from public.audit_log
    where session_id = 'R05-A42'
      and action_type in (
        'access_revoke'::public.audit_action,
        'document_archive'::public.audit_action,
        'security_event'::public.audit_action
      )
      and (
        document_id = '{ids["document_id"]}'::uuid
        or details @> jsonb_build_object('actor_id','{actor_id}')
      )
  )
)) as post_retire_verification;
"""


def create_command(args: argparse.Namespace) -> int:
    runtime_path = Path(args.runtime_file).expanduser().resolve()
    validate_runtime_path(runtime_path)
    if runtime_path.exists():
        raise RuntimeError(f"Runtime file đã tồn tại: {runtime_path}")

    service_key, anon_key = load_project_keys()
    password = secrets.token_urlsafe(36)
    marker = uuid.uuid4().hex[:12]
    email = f"crave-r05-a42-{marker}@invalid.example"
    actor_id: Optional[str] = None
    try:
        actor_id = create_user(service_key, email, password)
        token, expires_in = sign_in(anon_key, email, password)
        ids = fixture_ids()
        git_commit = run_cli(["git", "rev-parse", "HEAD"]).stdout.strip().lower()
        if len(git_commit) != 40 or any(char not in "0123456789abcdef" for char in git_commit):
            raise RuntimeError("HEAD không phải git SHA 40-hex hợp lệ.")

        generated = {
            "seed": ROOT / "work/r05_a42_live_seed_fixture.generated.sql",
            "verify_fixture": ROOT / "work/r05_a42_live_verify_fixture.generated.sql",
            "verify_evidence": ROOT / "work/r05_a42_live_verify_evidence.generated.sql",
            "retire": ROOT / "work/r05_a42_live_retire_fixture.generated.sql",
            "post_retire_verify": ROOT / "work/r05_a42_live_post_retire_verify.generated.sql",
        }
        generated["seed"].write_text(
            seed_sql(actor_id, email, ids, git_commit), encoding="utf-8"
        )
        generated["verify_fixture"].write_text(
            verify_fixture_sql(actor_id, ids), encoding="utf-8"
        )
        generated["verify_evidence"].write_text(
            verify_evidence_sql(actor_id, ids, git_commit), encoding="utf-8"
        )
        generated["retire"].write_text(
            retire_sql(actor_id, email, ids), encoding="utf-8"
        )
        generated["post_retire_verify"].write_text(
            post_retire_verify_sql(actor_id, ids), encoding="utf-8"
        )

        runtime_payload = {
            "actor_id": actor_id,
            "email": email,
            "password": password,
            "access_token": token,
            "access_token_expires_in": expires_in,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "git_commit": git_commit,
            "fixture_ids": ids,
            "generated_sql": {
                key: str(path.relative_to(ROOT)) for key, path in generated.items()
            },
        }
        write_secure_json(runtime_path, runtime_payload)
        manifest = {
            "projectRef": PROJECT_REF,
            "actor": {
                "id": actor_id,
                "email": email,
                "retainedIdentity": True,
                "hardDeleteAllowed": False,
                "initialState": "ACTIVE_SHORT_LIVED",
            },
            "gitCommit": git_commit,
            "workflow": {
                "name": WORKFLOW_NAME,
                "version": WORKFLOW_VERSION,
                "releaseCandidate": RELEASE_CANDIDATE,
            },
            "fixtureIds": ids,
            "runtimeSecretFile": str(runtime_path),
            "runtimeSecretFileMode": "0600",
            "generatedSql": runtime_payload["generated_sql"],
            "secretsPrinted": False,
        }
        manifest_path = ROOT / "work/r05_a42_live_actor_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "actor_id": actor_id,
                    "email": email,
                    "git_commit": git_commit,
                    "runtime_file": str(runtime_path),
                    "manifest": str(manifest_path.relative_to(ROOT)),
                    "generated_sql": runtime_payload["generated_sql"],
                    "secrets_printed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception:
        if actor_id:
            try:
                ban_user(service_key, actor_id)
            except Exception:
                pass
        raise
    finally:
        service_key = ""
        anon_key = ""
        password = ""


def load_runtime(path: Path) -> dict[str, Any]:
    validate_runtime_path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    uuid.UUID(payload["actor_id"])
    return payload


def regenerate_command(args: argparse.Namespace) -> int:
    runtime_path = Path(args.runtime_file).expanduser().resolve()
    runtime = load_runtime(runtime_path)
    actor_id = runtime["actor_id"]
    email = runtime["email"]
    ids = runtime["fixture_ids"]
    git_commit = run_cli(["git", "rev-parse", "HEAD"]).stdout.strip().lower()
    if len(git_commit) != 40 or any(char not in "0123456789abcdef" for char in git_commit):
        raise RuntimeError("HEAD không phải git SHA 40-hex hợp lệ.")
    generated = {
        "seed": ROOT / "work/r05_a42_live_seed_fixture.generated.sql",
        "verify_fixture": ROOT / "work/r05_a42_live_verify_fixture.generated.sql",
        "verify_evidence": ROOT / "work/r05_a42_live_verify_evidence.generated.sql",
        "retire": ROOT / "work/r05_a42_live_retire_fixture.generated.sql",
        "post_retire_verify": ROOT / "work/r05_a42_live_post_retire_verify.generated.sql",
    }
    generated["seed"].write_text(
        seed_sql(actor_id, email, ids, git_commit), encoding="utf-8"
    )
    generated["verify_fixture"].write_text(
        verify_fixture_sql(actor_id, ids), encoding="utf-8"
    )
    generated["verify_evidence"].write_text(
        verify_evidence_sql(actor_id, ids, git_commit), encoding="utf-8"
    )
    generated["retire"].write_text(
        retire_sql(actor_id, email, ids), encoding="utf-8"
    )
    generated["post_retire_verify"].write_text(
        post_retire_verify_sql(actor_id, ids), encoding="utf-8"
    )
    runtime["git_commit"] = git_commit
    runtime["generated_sql"] = {
        key: str(path.relative_to(ROOT)) for key, path in generated.items()
    }
    runtime["regenerated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    rewrite_secure_json(runtime_path, runtime)

    manifest_path = ROOT / "work/r05_a42_live_actor_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["gitCommit"] = git_commit
    manifest["generatedSql"] = runtime["generated_sql"]
    manifest["regeneratedAt"] = runtime["regenerated_at"]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "actor_id": actor_id,
                "git_commit": git_commit,
                "generated_sql": runtime["generated_sql"],
                "runtime_secrets_unchanged": True,
                "secrets_printed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def token_command(args: argparse.Namespace) -> int:
    runtime = load_runtime(Path(args.runtime_file).expanduser().resolve())
    token = runtime.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Runtime file không có access token.")
    print(token)
    return 0


def refresh_token_command(args: argparse.Namespace) -> int:
    """Issue a fresh short-lived JWT for the retained actor without creating a user."""
    runtime_path = Path(args.runtime_file).expanduser().resolve()
    runtime = load_runtime(runtime_path)
    email = runtime.get("email")
    password = runtime.get("password")
    if not isinstance(email, str) or not email:
        raise RuntimeError("Runtime file không có email actor.")
    if not isinstance(password, str) or not password:
        raise RuntimeError("Runtime file không có password actor.")

    _service_key, anon_key = load_project_keys()
    try:
        token, expires_in = sign_in(anon_key, email, password)
        runtime["access_token"] = token
        runtime["access_token_expires_in"] = expires_in
        runtime["access_token_refreshed_at"] = dt.datetime.now(
            dt.timezone.utc
        ).isoformat()
        rewrite_secure_json(runtime_path, runtime)
        print(
            json.dumps(
                {
                    "actor_id": runtime["actor_id"],
                    "access_token_expires_in": expires_in,
                    "refreshed_at": runtime["access_token_refreshed_at"],
                    "runtime_file": str(runtime_path),
                    "new_actor_created": False,
                    "secrets_printed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        anon_key = ""
        password = ""


def ban_command(args: argparse.Namespace) -> int:
    runtime_path = Path(args.runtime_file).expanduser().resolve()
    runtime = load_runtime(runtime_path)
    service_key, _anon_key = load_project_keys()
    try:
        result = ban_user(service_key, runtime["actor_id"])
        retirement_path = ROOT / "work/r05_a42_live_actor_retirement.json"
        retirement_path.write_text(
            json.dumps(
                {
                    **result,
                    "projectRef": PROJECT_REF,
                    "retiredAt": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "runtimeSecretsPurged": bool(args.purge_runtime_secrets),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if args.purge_runtime_secrets:
            runtime_path.unlink()
        print(
            json.dumps(
                {
                    **result,
                    "retirement_manifest": str(retirement_path.relative_to(ROOT)),
                    "runtime_secrets_purged": bool(args.purge_runtime_secrets),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        service_key = ""


def dry_run() -> int:
    print(
        json.dumps(
            {
                "mode": "dry-run",
                "projectRef": PROJECT_REF,
                "plannedAuthActors": 1,
                "plannedRetainedProfiles": 1,
                "plannedTemporaryQaManagerRoles": 1,
                "plannedSyntheticDocuments": 1,
                "plannedRawFiles": 1,
                "plannedCurrentDocumentVersions": 1,
                "plannedChunksWithCopied1536Embedding": 1,
                "plannedDirectAccessRows": 1,
                "plannedGoldenQuestions": 5,
                "plannedRetrievalProfiles": 1,
                "plannedEvalDatasets": 1,
                "retirement": [
                    "ban Auth actor; retain identity",
                    "deactivate user profile, role, direct access, golden questions",
                    "retire retrieval profile and eval dataset",
                    "archive/deny AI for document, version, chunk",
                    "retain append-only evidence and audit rows",
                ],
                "hardDelete": False,
                "secrets": "mode-0600 private runtime only; never included in reports",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("dry-run")

    create = subcommands.add_parser("create")
    create.add_argument("--runtime-file", required=True)
    create.add_argument("--i-understand-live-auth-mutation", action="store_true")

    token = subcommands.add_parser("token")
    token.add_argument("--runtime-file", required=True)

    refresh_token = subcommands.add_parser("refresh-token")
    refresh_token.add_argument("--runtime-file", required=True)
    refresh_token.add_argument(
        "--i-understand-live-auth-mutation", action="store_true"
    )

    regenerate = subcommands.add_parser("regenerate")
    regenerate.add_argument("--runtime-file", required=True)

    ban = subcommands.add_parser("ban")
    ban.add_argument("--runtime-file", required=True)
    ban.add_argument("--purge-runtime-secrets", action="store_true")
    ban.add_argument("--i-understand-live-auth-mutation", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.command == "dry-run":
        return dry_run()
    if args.command == "create":
        if not args.i_understand_live_auth_mutation:
            raise SystemExit("create requires --i-understand-live-auth-mutation")
        return create_command(args)
    if args.command == "token":
        return token_command(args)
    if args.command == "refresh-token":
        if not args.i_understand_live_auth_mutation:
            raise SystemExit(
                "refresh-token requires --i-understand-live-auth-mutation"
            )
        return refresh_token_command(args)
    if args.command == "regenerate":
        return regenerate_command(args)
    if args.command == "ban":
        if not args.i_understand_live_auth_mutation:
            raise SystemExit("ban requires --i-understand-live-auth-mutation")
        return ban_command(args)
    raise SystemExit("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
