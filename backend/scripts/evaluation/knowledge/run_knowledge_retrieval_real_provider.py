from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

# backend/scripts/evaluation/knowledge/<runner>.py -> backend
BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.core.config import settings
from app.dependencies.db import SessionLocal
from app.services.embedding_provider import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from app.services.retrieval_evaluation import RetrievalEvaluationObservation, aggregate_observations
from app.services.retrieval_evaluation_baseline import build_baseline, compare_baseline, write_baseline
from app.services.retrieval_evaluation_dataset import load_retrieval_evaluation_dataset
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRecord
from scripts.evaluation.knowledge.run_knowledge_retrieval_evaluation import (
    DATASET,
    FIXTURE,
    KB_ID,
    VERSION_ID,
    actual_chunk_id,
    cleanup_fixture,
    load_jsonl,
    prepare_fixture,
)

BASELINE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_real_baseline.json"


def _require_real_provider() -> None:
    if settings.embedding_provider != "openai-compatible":
        raise SystemExit(
            "Real Provider Quality Gate requires EMBEDDING_PROVIDER=openai-compatible"
        )
    if not settings.embedding_base_url:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_BASE_URL")
    if not settings.embedding_api_key:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_API_KEY")
    if not settings.embedding_model:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_MODEL")
    if settings.vector_provider != "pgvector":
        raise SystemExit("Real Provider Quality Gate requires VECTOR_PROVIDER=pgvector")
    if settings.embedding_dimension < 1:
        raise SystemExit("EMBEDDING_DIMENSION must be greater than zero")


def _dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def run(k: int, baseline_path: Path, freeze_baseline: bool) -> int:
    _require_real_provider()
    dataset = load_retrieval_evaluation_dataset(DATASET)
    fixtures = load_jsonl(FIXTURE)
    fixture_by_id = {row["chunk_id"]: row for row in fixtures}
    missing = sorted(
        {
            chunk_id
            for case in dataset.cases
            for chunk_id in case.relevant_chunk_ids
            if chunk_id not in fixture_by_id
        }
    )
    if missing:
        raise SystemExit(f"evaluation fixture missing relevant chunks: {missing}")

    provider = OpenAICompatibleEmbeddingProvider(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        timeout_seconds=settings.embedding_timeout_seconds,
        dimensions=(
            settings.embedding_dimension
            if settings.embedding_dimensions_parameter_enabled
            else None
        ),
        expected_dimension=settings.embedding_dimension,
    )
    metadata = {
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "dataset_version": dataset.schema_version,
        "dataset_sha256": _dataset_sha256(DATASET),
        "retrieval_mode": "real-provider-pgvector",
        "top_k": k,
    }

    async with SessionLocal() as db:
        owner = (await db.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))).scalar_one_or_none()
        if owner is None:
            raise SystemExit("evaluation runner requires at least one user in the database")
        owner = uuid.UUID(str(owner))
        await prepare_fixture(db, fixtures, owner)
        try:
            observations: list[RetrievalEvaluationObservation] = []
            case_reports: list[dict[str, object]] = []
            vector_provider = PgVectorRetrievalProvider(db, settings.embedding_dimension)

            started = time.perf_counter()
            try:
                fixture_embeddings = await provider.embed([row["content"] for row in fixtures])
            except EmbeddingProviderError as exc:
                error = f"{type(exc).__name__}: {exc}"
                latency_ms = round((time.perf_counter() - started) * 1000, 3)
                observations = [
                    RetrievalEvaluationObservation((), latency_ms, error)
                    for _ in dataset.cases
                ]
                case_reports = [
                    {
                        "query": case.query,
                        "relevant_chunk_ids": sorted(case.relevant_chunk_ids),
                        "retrieved_chunk_ids": [],
                        "latency_ms": latency_ms,
                        "error": error,
                    }
                    for case in dataset.cases
                ]
            else:
                records = [
                    VectorRecord(
                        chunk_id=str(actual_chunk_id(row["chunk_id"])),
                        embedding=tuple(embedding),
                        metadata={
                            "knowledge_base_id": str(KB_ID),
                            "document_version_id": str(VERSION_ID),
                            "evaluation_chunk_id": row["chunk_id"],
                        },
                    )
                    for row, embedding in zip(fixtures, fixture_embeddings, strict=True)
                ]
                await vector_provider.upsert(records)

                for case in dataset.cases:
                    started = time.perf_counter()
                    error = None
                    ranking: list[str] = []
                    try:
                        query_embedding = (await provider.embed([case.query]))[0]
                        results = await vector_provider.search(
                            query_embedding,
                            top_k=k,
                            min_score=0.0,
                            knowledge_base_id=str(KB_ID),
                        )
                        ranking = [
                            result.metadata.get("evaluation_chunk_id", result.chunk_id)
                            for result in results
                        ]
                    except Exception as exc:  # provider failures remain visible in observations
                        error = f"{type(exc).__name__}: {exc}"
                    latency_ms = round((time.perf_counter() - started) * 1000, 3)
                    observations.append(
                        RetrievalEvaluationObservation(tuple(ranking), latency_ms, error)
                    )
                    case_reports.append(
                        {
                            "query": case.query,
                            "relevant_chunk_ids": sorted(case.relevant_chunk_ids),
                            "retrieved_chunk_ids": ranking,
                            "latency_ms": latency_ms,
                            "error": error,
                        }
                    )

            metrics = aggregate_observations(dataset.cases, observations, k=k)
            baseline_status = "not_checked"
            failures: list[str] = []
            if freeze_baseline:
                if metrics["error_rate"] > 0:
                    failures.append(
                        f"cannot freeze baseline with provider error rate {metrics['error_rate']}"
                    )
                elif baseline_path.exists():
                    failures.append(
                        f"baseline already exists: {baseline_path}; review the existing baseline before replacing it"
                    )
                else:
                    write_baseline(baseline_path, build_baseline(metadata, metrics))
                    baseline_status = "created"
            elif not baseline_path.exists():
                baseline_status = "missing"
                failures.append(f"real provider baseline is missing: {baseline_path}")
            else:
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                failures.extend(compare_baseline(metadata, metrics, baseline))
                baseline_status = "checked"

            report = {
                "dataset": {
                    "path": str(dataset.source),
                    "schema_version": dataset.schema_version,
                    "sha256": metadata["dataset_sha256"],
                },
                **metadata,
                "source": "postgresql/pgvector",
                "fallback_count": 0,
                "fallback_used": False,
                "baseline": {
                    "path": str(baseline_path),
                    "status": baseline_status,
                },
                **metrics,
                "cases_detail": case_reports,
                "quality_gate": "passed" if baseline_status == "checked" and not failures else (
                    "baseline_created" if baseline_status == "created" and not failures else "failed"
                ),
                "failures": failures,
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if failures else 0
        finally:
            await cleanup_fixture(db)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Retrieval Quality Gate with a real OpenAI-compatible embedding provider and PostgreSQL/pgvector"
    )
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument(
        "--freeze-baseline",
        action="store_true",
        help="Create the real-provider baseline from this run; the result is not marked as a quality-gate pass",
    )
    args = parser.parse_args()
    if args.k < 1:
        raise SystemExit("--k must be greater than zero")
    return asyncio.run(run(args.k, args.baseline, args.freeze_baseline))


if __name__ == "__main__":
    raise SystemExit(main())
