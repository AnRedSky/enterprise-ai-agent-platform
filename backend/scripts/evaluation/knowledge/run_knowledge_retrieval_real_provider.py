from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.core.config import settings
from app.dependencies.db import SessionLocal
from app.services.embedding_provider import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from app.services.ollama_embedding_provider import OllamaEmbeddingProvider
from app.services.retrieval_evaluation import RetrievalEvaluationObservation, aggregate_observations
from app.services.retrieval_evaluation_baseline import build_baseline, build_regression_report, compare_baseline, write_baseline
from app.services.retrieval_evaluation_dataset import load_retrieval_evaluation_dataset
from app.services.retrieval_evaluation_trace import RetrievalEvaluationTraceService
from app.services.vector_knowledge_retrieval import VectorKnowledgeRetrievalService
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRecord
from scripts.evaluation.knowledge.run_knowledge_retrieval_evaluation import DATASET, FIXTURE, KB_ID, VERSION_ID, actual_chunk_id, cleanup_fixture, load_jsonl, prepare_fixture

BASELINE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_real_baseline.json"


def _require_real_provider() -> None:
    if settings.embedding_provider not in {"openai-compatible", "ollama"}:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_PROVIDER=openai-compatible or ollama")
    if not settings.embedding_base_url:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_BASE_URL")
    if settings.embedding_provider == "openai-compatible" and not settings.embedding_api_key:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_API_KEY for openai-compatible")
    if not settings.embedding_model:
        raise SystemExit("Real Provider Quality Gate requires EMBEDDING_MODEL")
    if settings.vector_provider != "pgvector":
        raise SystemExit("Real Provider Quality Gate requires VECTOR_PROVIDER=pgvector")
    if settings.embedding_dimension < 1:
        raise SystemExit("EMBEDDING_DIMENSION must be greater than zero")


def _dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_embedding_provider():
    common = {"model": settings.embedding_model, "timeout_seconds": settings.embedding_timeout_seconds, "dimensions": settings.embedding_dimension if settings.embedding_dimensions_parameter_enabled else None, "expected_dimension": settings.embedding_dimension}
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(base_url=settings.embedding_base_url, **common)
    return OpenAICompatibleEmbeddingProvider(base_url=settings.embedding_base_url, api_key=settings.embedding_api_key, **common)


async def run(k: int, baseline_path: Path, freeze_baseline: bool) -> int:
    _require_real_provider()
    dataset = load_retrieval_evaluation_dataset(DATASET)
    fixtures = load_jsonl(FIXTURE)
    fixture_by_id = {row["chunk_id"]: row for row in fixtures}
    missing = sorted({chunk_id for case in dataset.cases for chunk_id in case.relevant_chunk_ids if chunk_id not in fixture_by_id})
    if missing:
        raise SystemExit(f"evaluation fixture missing relevant chunks: {missing}")

    provider = _build_embedding_provider()
    evaluation_run_id = str(uuid.uuid4())
    metadata = {"evaluation_run_id": evaluation_run_id, "provider": settings.embedding_provider, "model": settings.embedding_model, "embedding_dimension": settings.embedding_dimension, "dataset_version": dataset.schema_version, "dataset_sha256": _dataset_sha256(DATASET), "retrieval_mode": "real-provider-pgvector", "retrieval_execution_path": "runtime-service", "top_k": k, "citation_source": "runtime-retrieval-result"}

    async with SessionLocal() as db:
        owner_row = (await db.execute(text("SELECT id, tenant_id FROM users ORDER BY id LIMIT 1"))).first()
        if owner_row is None:
            raise SystemExit("evaluation runner requires at least one user in the database")
        owner = uuid.UUID(str(owner_row[0]))
        tenant_id = uuid.UUID(str(owner_row[1])) if owner_row[1] else None
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
                observations = [RetrievalEvaluationObservation((), latency_ms, error, ()) for _ in dataset.cases]
                case_reports = [{"query": case.query, "relevant_chunk_ids": sorted(case.relevant_chunk_ids), "expected_citation_targets": sorted(case.expected_citation_targets), "retrieved_chunk_ids": [], "cited_chunk_ids": [], "citations": [], "latency_ms": latency_ms, "error": error} for case in dataset.cases]
            else:
                records = [VectorRecord(chunk_id=str(actual_chunk_id(row["chunk_id"])), embedding=tuple(embedding), metadata={"knowledge_base_id": str(KB_ID), "document_version_id": str(VERSION_ID), "evaluation_chunk_id": row["chunk_id"]}) for row, embedding in zip(fixtures, fixture_embeddings, strict=True)]
                await vector_provider.upsert(records)
                await db.execute(text("UPDATE knowledge_document_versions SET vector_index_status = 'ready' WHERE id = :version"), {"version": str(VERSION_ID)})
                await db.commit()
                evaluation_service = VectorKnowledgeRetrievalService(db)
                actual_to_evaluation = {str(actual_chunk_id(row["chunk_id"])): row["chunk_id"] for row in fixtures}
                for case in dataset.cases:
                    started = time.perf_counter()
                    error = None
                    ranking: list[str] = []
                    cited_chunk_ids: list[str] = []
                    citations: list[dict[str, object]] = []
                    try:
                        results = await evaluation_service.retrieve(query=case.query, top_k=k, owner_id=owner, is_admin=False, knowledge_base_id=KB_ID)
                        for result in results:
                            evaluation_chunk_id = actual_to_evaluation.get(str(result["chunk_id"]))
                            if evaluation_chunk_id is None:
                                continue
                            ranking.append(evaluation_chunk_id)
                            cited_chunk_ids.append(evaluation_chunk_id)
                            citations.append({"chunk_id": evaluation_chunk_id, "citation": result["citation"], "source_document": result["source_document"], "source_uri": result["source_uri"], "relevance_score": result["relevance_score"]})
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                    latency_ms = round((time.perf_counter() - started) * 1000, 3)
                    observations.append(RetrievalEvaluationObservation(tuple(ranking), latency_ms, error, tuple(cited_chunk_ids)))
                    case_reports.append({"query": case.query, "relevant_chunk_ids": sorted(case.relevant_chunk_ids), "expected_citation_targets": sorted(case.expected_citation_targets), "retrieved_chunk_ids": ranking, "cited_chunk_ids": cited_chunk_ids, "citations": citations, "latency_ms": latency_ms, "error": error})

            metrics = aggregate_observations(dataset.cases, observations, k=k)
            baseline_status = "not_checked"
            failures: list[str] = []
            regression = None
            if freeze_baseline:
                if metrics["error_rate"] > 0:
                    failures.append(f"cannot freeze baseline with provider error rate {metrics['error_rate']}")
                elif baseline_path.exists():
                    failures.append(f"baseline already exists: {baseline_path}; review the existing baseline before replacing it")
                else:
                    write_baseline(baseline_path, build_baseline(metadata, metrics))
                    baseline_status = "created"
            elif not baseline_path.exists():
                baseline_status = "missing"
                failures.append(f"real provider baseline is missing: {baseline_path}")
            else:
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                regression = build_regression_report(metadata, metrics, baseline)
                failures.extend(compare_baseline(metadata, metrics, baseline))
                baseline_status = "checked"

            quality_gate = "passed" if baseline_status == "checked" and not failures else ("baseline_created" if baseline_status == "created" and not failures else "failed")
            report = {"dataset": {"path": str(dataset.source), "schema_version": dataset.schema_version, "sha256": metadata["dataset_sha256"]}, **metadata, "source": "postgresql/pgvector", "fallback_count": 0, "fallback_used": False, "baseline": {"path": str(baseline_path), "status": baseline_status}, "regression": regression, **metrics, "cases_detail": case_reports, "quality_gate": quality_gate, "failures": failures}
            await RetrievalEvaluationTraceService(db).record_run(evaluation_run_id=evaluation_run_id, owner_id=owner, tenant_id=tenant_id, metadata=metadata, case_reports=case_reports, metrics=metrics, regression=regression, quality_gate=quality_gate, failures=failures)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if failures else 0
        finally:
            await cleanup_fixture(db)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Retrieval Quality Gate through the real runtime retrieval service with a real embedding provider and PostgreSQL/pgvector")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--freeze-baseline", action="store_true")
    args = parser.parse_args()
    if args.k < 1:
        raise SystemExit("--k must be greater than zero")
    return asyncio.run(run(args.k, args.baseline, args.freeze_baseline))


if __name__ == "__main__":
    raise SystemExit(main())
