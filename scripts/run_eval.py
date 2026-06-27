#!/usr/bin/env python3
"""Chạy bộ đánh giá RAG và lưu kết quả vào Supabase.

Biến môi trường bắt buộc:
  SUPABASE_URL, SUPABASE_KEY, WEBHOOK_BASE, OPENAI_API_KEY

Xác thực người dùng chọn một trong hai cách:
  - EVAL_JWT; hoặc
  - EVAL_EMAIL và EVAL_PASSWORD (cũng chấp nhận SUPABASE_EMAIL/PASSWORD).

Biến tùy chọn:
  EVAL_MODEL_TAG, EVAL_JUDGE_MODEL, EVAL_EMBEDDING_MODEL, EVAL_HTTP_TIMEOUT
"""

from __future__ import annotations

import asyncio
import json
import math
import os
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Awaitable, Iterable

import requests
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, ContextRecall, Faithfulness
from supabase import Client, create_client


PASS_THRESHOLD = 0.90
DEFAULT_HTTP_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class Config:
    supabase_url: str
    supabase_key: str
    webhook_base: str
    openai_api_key: str
    eval_jwt: str | None
    eval_email: str | None
    eval_password: str | None
    model_tag: str
    judge_model: str
    embedding_model: str
    http_timeout: float


@dataclass(frozen=True)
class GoldenQuestion:
    question_id: str
    question: str
    reference: str
    expected_keywords: list[str]
    language: str


@dataclass
class EvaluationResult:
    question_id: str
    answer: str
    faithfulness: float
    relevancy: float
    context_recall: float
    grounded_pct: float
    passed: bool
    raw_json: dict[str, Any]

    @property
    def score_mean(self) -> float:
        return fmean((self.faithfulness, self.relevancy, self.context_recall))


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường bắt buộc: {name}")
    return value


def load_config() -> Config:
    load_dotenv()

    try:
        http_timeout = float(
            os.getenv("EVAL_HTTP_TIMEOUT", str(DEFAULT_HTTP_TIMEOUT_SECONDS))
        )
    except ValueError as exc:
        raise RuntimeError("EVAL_HTTP_TIMEOUT phải là một số dương") from exc

    if http_timeout <= 0:
        raise RuntimeError("EVAL_HTTP_TIMEOUT phải lớn hơn 0")

    return Config(
        supabase_url=require_env("SUPABASE_URL").rstrip("/"),
        supabase_key=require_env("SUPABASE_KEY"),
        webhook_base=require_env("WEBHOOK_BASE").rstrip("/"),
        openai_api_key=require_env("OPENAI_API_KEY"),
        eval_jwt=os.getenv("EVAL_JWT", "").strip() or None,
        eval_email=(
            os.getenv("EVAL_EMAIL", "").strip()
            or os.getenv("SUPABASE_EMAIL", "").strip()
            or None
        ),
        eval_password=(
            os.getenv("EVAL_PASSWORD", "").strip()
            or os.getenv("SUPABASE_PASSWORD", "").strip()
            or None
        ),
        model_tag=os.getenv("EVAL_MODEL_TAG", "rag-query").strip() or "rag-query",
        judge_model=(
            os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini").strip()
            or "gpt-4o-mini"
        ),
        embedding_model=(
            os.getenv("EVAL_EMBEDDING_MODEL", "text-embedding-3-small").strip()
            or "text-embedding-3-small"
        ),
        http_timeout=http_timeout,
    )


def authenticate(client: Client, config: Config) -> str:
    """Trả JWT authenticated và cấu hình cùng JWT cho PostgREST."""

    if config.eval_jwt:
        client.postgrest.auth(config.eval_jwt)
        return config.eval_jwt

    if not config.eval_email or not config.eval_password:
        raise RuntimeError(
            "Cần EVAL_JWT hoặc cặp EVAL_EMAIL/EVAL_PASSWORD để gọi webhook "
            "và truy cập các bảng có RLS."
        )

    auth_response = client.auth.sign_in_with_password(
        {"email": config.eval_email, "password": config.eval_password}
    )
    if auth_response.session is None or not auth_response.session.access_token:
        raise RuntimeError("Supabase signInWithPassword không trả về access token")
    return auth_response.session.access_token


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def load_golden_questions(client: Client) -> list[GoldenQuestion]:
    response = client.table("golden_questions").select("*").execute()
    rows = response.data or []
    questions: list[GoldenQuestion] = []

    for row in rows:
        question_id = str(row.get("id") or "").strip()
        question = str(row.get("question") or row.get("question_text") or "").strip()
        expected_keywords = _string_list(
            row.get("expected_keywords") or row.get("expected_sources")
        )
        reference = str(row.get("expected_answer") or "").strip()
        if not reference and expected_keywords:
            reference = "; ".join(expected_keywords)

        if not question_id or not question:
            raise RuntimeError("golden_questions có hàng thiếu id hoặc nội dung câu hỏi")
        if not reference:
            raise RuntimeError(
                f"Câu hỏi {question_id} thiếu expected_answer/expected_keywords"
            )

        questions.append(
            GoldenQuestion(
                question_id=question_id,
                question=question,
                reference=reference,
                expected_keywords=expected_keywords,
                language=str(row.get("question_language") or "vi"),
            )
        )

    if not questions:
        raise RuntimeError("golden_questions không có dữ liệu")
    return questions


def _response_answer(payload: dict[str, Any]) -> str:
    return str(payload.get("answer") or payload.get("message") or "").strip()


def _context_text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""

    for key in ("content", "chunk_text", "text", "snippet", "claim_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_contexts(payload: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []
    for key in ("retrieved_contexts", "contexts", "sources", "citations"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(value)

    contexts: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        context = _context_text(candidate)
        if context and context not in seen:
            contexts.append(context)
            seen.add(context)
    return contexts


def _normalize_ratio(value: Any) -> float | None:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(ratio):
        return None
    if ratio > 1.0 and ratio <= 100.0:
        ratio /= 100.0
    return min(1.0, max(0.0, ratio))


def calculate_grounded_pct(payload: dict[str, Any]) -> float:
    explicit = _normalize_ratio(payload.get("grounded_pct"))
    if explicit is not None:
        return explicit

    source_items: list[Any] = []
    for key in ("sources", "citations"):
        value = payload.get(key)
        if isinstance(value, list):
            source_items.extend(value)

    flags = [
        item["grounded"]
        for item in source_items
        if isinstance(item, dict) and isinstance(item.get("grounded"), bool)
    ]
    if not flags:
        return 0.0
    return sum(1 for flag in flags if flag) / len(flags)


def call_rag_webhook(
    session: requests.Session,
    config: Config,
    jwt: str,
    golden: GoldenQuestion,
) -> dict[str, Any]:
    response = session.post(
        f"{config.webhook_base}/rag-query",
        headers={
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        },
        json={
            "query": golden.question,
            "response_language": golden.language,
            "filters": {"language_preference": golden.language},
        },
        timeout=config.http_timeout,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise RuntimeError("Webhook rag-query không trả JSON hợp lệ") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Webhook rag-query phải trả về một JSON object")
    if payload.get("success") is False:
        raise RuntimeError(str(payload.get("error") or "rag-query báo thất bại"))
    if not _response_answer(payload):
        raise RuntimeError("Webhook rag-query không trả answer/message")
    return payload


def _score_value(result: Any) -> float:
    raw_value = getattr(result, "value", result)
    score = _normalize_ratio(raw_value)
    if score is None:
        raise ValueError(f"Ragas trả điểm không hợp lệ: {raw_value!r}")
    return score


async def _safe_metric(
    name: str,
    operation: Awaitable[Any],
) -> tuple[str, float, str | None]:
    try:
        result = await operation
        return name, _score_value(result), None
    except Exception as exc:  # Ragas/provider error belongs in raw_json per row.
        return name, 0.0, f"{type(exc).__name__}: {exc}"


async def evaluate_question(
    golden: GoldenQuestion,
    payload: dict[str, Any],
    faithfulness_metric: Faithfulness,
    relevancy_metric: AnswerRelevancy,
    context_recall_metric: ContextRecall,
) -> EvaluationResult:
    answer = _response_answer(payload)
    contexts = extract_contexts(payload)

    metric_results = await asyncio.gather(
        _safe_metric(
            "faithfulness",
            faithfulness_metric.ascore(
                user_input=golden.question,
                response=answer,
                retrieved_contexts=contexts,
            ),
        ),
        _safe_metric(
            "answer_relevancy",
            relevancy_metric.ascore(
                user_input=golden.question,
                response=answer,
            ),
        ),
        _safe_metric(
            "context_recall",
            context_recall_metric.ascore(
                user_input=golden.question,
                retrieved_contexts=contexts,
                reference=golden.reference,
            ),
        ),
    )

    scores = {name: value for name, value, _ in metric_results}
    metric_errors = {
        name: error for name, _, error in metric_results if error is not None
    }
    grounded_pct = calculate_grounded_pct(payload)
    question_score = fmean(scores.values())

    return EvaluationResult(
        question_id=golden.question_id,
        answer=answer,
        faithfulness=scores["faithfulness"],
        relevancy=scores["answer_relevancy"],
        context_recall=scores["context_recall"],
        grounded_pct=grounded_pct,
        passed=question_score >= PASS_THRESHOLD,
        raw_json={
            "webhook": payload,
            "expected_keywords": golden.expected_keywords,
            "retrieved_context_count": len(contexts),
            "metric_errors": metric_errors,
            "score_mean": round(question_score, 4),
        },
    )


def failed_result(golden: GoldenQuestion, exc: Exception) -> EvaluationResult:
    return EvaluationResult(
        question_id=golden.question_id,
        answer="",
        faithfulness=0.0,
        relevancy=0.0,
        context_recall=0.0,
        grounded_pct=0.0,
        passed=False,
        raw_json={"webhook_error": f"{type(exc).__name__}: {exc}"},
    )


def _chunks(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def persist_results(
    client: Client,
    config: Config,
    results: list[EvaluationResult],
) -> tuple[str, float, float, bool]:
    question_scores = [result.score_mean for result in results]
    score_mean = fmean(question_scores)
    score_min = min(question_scores)
    passed = score_mean >= PASS_THRESHOLD

    run_response = (
        client.table("eval_runs")
        .insert(
            {
                "model_tag": config.model_tag,
                "n_questions": len(results),
                "score_mean": round(score_mean, 4),
                "score_min": round(score_min, 4),
                "passed": passed,
                "notes": (
                    f"Ragas judge={config.judge_model}; "
                    f"embedding={config.embedding_model}; "
                    f"pass_threshold={PASS_THRESHOLD:.2f}"
                ),
            }
        )
        .execute()
    )
    if not run_response.data:
        raise RuntimeError("Không nhận được id sau khi INSERT eval_runs")
    run_id = str(run_response.data[0]["id"])

    result_rows = [
        {
            "run_id": run_id,
            "question_id": result.question_id,
            "answer": result.answer,
            "score_faithfulness": round(result.faithfulness, 4),
            "score_relevancy": round(result.relevancy, 4),
            "score_context_recall": round(result.context_recall, 4),
            "grounded_pct": round(result.grounded_pct, 4),
            "passed": result.passed,
            "raw_json": result.raw_json,
        }
        for result in results
    ]
    for batch in _chunks(result_rows, 100):
        client.table("eval_results").insert(batch).execute()

    return run_id, score_mean, score_min, passed


async def run() -> None:
    config = load_config()
    supabase = create_client(config.supabase_url, config.supabase_key)
    jwt = authenticate(supabase, config)
    golden_questions = load_golden_questions(supabase)

    openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    evaluator_llm = llm_factory(config.judge_model, client=openai_client)
    evaluator_embeddings = embedding_factory(
        "openai",
        model=config.embedding_model,
        client=openai_client,
    )
    faithfulness_metric = Faithfulness(llm=evaluator_llm)
    relevancy_metric = AnswerRelevancy(
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    context_recall_metric = ContextRecall(llm=evaluator_llm)

    results: list[EvaluationResult] = []
    http_session = requests.Session()
    try:
        for index, golden in enumerate(golden_questions, start=1):
            print(f"[{index}/{len(golden_questions)}] {golden.question}")
            try:
                payload = call_rag_webhook(http_session, config, jwt, golden)
                result = await evaluate_question(
                    golden,
                    payload,
                    faithfulness_metric,
                    relevancy_metric,
                    context_recall_metric,
                )
            except Exception as exc:
                result = failed_result(golden, exc)
                print(f"  lỗi: {type(exc).__name__}: {exc}")
            results.append(result)
            print(
                "  faithfulness={:.4f} relevancy={:.4f} "
                "context_recall={:.4f} grounded_pct={:.4f} passed={}".format(
                    result.faithfulness,
                    result.relevancy,
                    result.context_recall,
                    result.grounded_pct,
                    result.passed,
                )
            )
    finally:
        http_session.close()
        await openai_client.close()

    run_id, score_mean, score_min, passed = persist_results(
        supabase, config, results
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "score_mean": round(score_mean, 4),
                "score_min": round(score_min, 4),
                "passed": passed,
                "threshold": PASS_THRESHOLD,
                "n_questions": len(results),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
