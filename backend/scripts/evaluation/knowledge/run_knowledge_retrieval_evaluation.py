from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from sqlalchemy import text

# backend/scripts/evaluation/knowledge/<runner>.py -> backend
BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.dependencies.db import SessionLocal
from app.services.mock_embedding_provider import MockEmbeddingProvider
from app.services.retrieval_evaluation import (
    RetrievalEvaluationObservation,
    aggregate_observations,
)
from app.services.retrieval_evaluation_dataset import load_retrieval_evaluation_dataset
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRecord

DATASET = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_dataset.jsonl"
FIXTURE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_fixture.jsonl"
BASELINE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_baseline.json"
FIXTURE_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000100")
KB_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
DOC_ID = uuid.UUID("00000000-0000-0000-0000-000000000102")
VERSION_ID = uuid.UUID("00000000-0000-0000-0000-000000000103")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def actual_chunk_id(evaluation_chunk_id: str) -> uuid.UUID:
    return uuid.uuid5(FIXTURE_NAMESPACE, evaluation_chunk_id)


def quality_gate(metrics: dict[str, float | int], baseline: dict) -> list[str]:
    failures: list[str] = []
    for metric in ("recall_at_k", "mrr"):
        actual = float(metrics[metric])
        expected = float(baseline.get(metric, 0.0))
        if actual < expected:
            failures.append(f"{metric} regressed: {actual} < baseline {expected}")
    if float(metrics["error_rate"]) > 0:
        failures.append(f"provider error rate is non-zero: {metrics['error_rate']}")
    return failures


async def prepare_fixture(db, rows: list[dict], user_id: uuid.UUID) -> None:
    await db.execute(text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :kb"), {"kb": str(KB_ID)})
    await db.execute(text("DELETE FROM knowledge_document_chunks WHERE document_version_id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_document_versions WHERE id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_documents WHERE id = :doc"), {"doc": str(DOC_ID)})
    await db.execute(text("DELETE FROM knowledge_bases WHERE id = :kb"), {"kb": str(KB_ID)})

    await db.execute(text("""
        INSERT INTO knowledge_bases
            (id, name, description, owner_id, status, created_at, updated_at)
        VALUES
            (:id, 'Phase 2.2-B Evaluation Fixture',
             'Ephemeral deterministic retrieval evaluation data',
             :owner, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """), {"id": str(KB_ID), "owner": str(user_id)})
    await db.execute(text("""
        INSERT INTO knowledge_documents
            (id, knowledge_base_id, title, source_type, status, created_at, updated_at)
        VALUES
            (:id, :kb, 'Phase 2.2-B Evaluation Fixture', 'evaluation', 'active',
             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """), {"id": str(DOC_ID), "kb": str(KB_ID)})
    await db.execute(text("""
        INSERT INTO knowledge_document_versions
            (id, document_id, version, status, ingestion_status, vector_index_status, created_by, created_at)
        VALUES
            (:id, :doc, 'evaluation', 'published', 'completed', 'processing', :user, CURRENT_TIMESTAMP)
    """), {"id": str(VERSION_ID), "doc": str(DOC_ID), "user": str(user_id)})
    for index, row in enumerate(rows):
        chunk_id = actual_chunk_id(row["chunk_id"])
        content = row["content"]
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        await db.execute(text("""
            INSERT INTO knowledge_document_chunks
                (id, document_version_id, chunk_index, content, char_start, char_end,
                 content_hash, token_count, created_at)
            VALUES
                (:id, :version, :index, :content, 0, :char_end, :hash, :tokens, CURRENT_TIMESTAMP)
        """), {
            "id": str(chunk_id), "version": str(VERSION_ID), "index": index,
            "content": content, "char_end": len(content), "hash": digest,
            "tokens": len(content.split()),
        })
    await db.execute(
        text("UPDATE knowledge_documents SET current_version_id = :version WHERE id = :doc"),
        {"version": str(VERSION_ID), "doc": str(DOC_ID)},
    )
    await db.commit()


async def cleanup_fixture(db) -> None:
    await db.execute(text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :kb"), {"kb": str(KB_ID)})
    await db.execute(text("DELETE FROM knowledge_document_chunks WHERE document_version_id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_document_versions WHERE id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_documents WHERE id = :doc"), {"id": str(DOC_ID)})
    await db.execute(text("DELETE FROM knowledge_bases WHERE id = :kb"), {"kb": str(KB_ID)})
    await db.commit()


async def run(k: int) -> int:
    if settings.embedding_provider != "mock":
        raise SystemExit("Evaluation runner requires EMBEDDING_PROVIDER=mock for offline validation")
    if settings.vector_provider != "pgvector":
        raise SystemExit("Evaluation runner requires VECTOR_PROVIDER=pgvector")

    dataset = load_retrieval_evaluation_dataset(DATASET)
    fixtures = load_jsonl(FIXTURE)
    fixture_by_id = {row["chunk_id"]: row for row in fixtures}
    missing = sorted({chunk_id for case in dataset.cases for chunk_id in case.relevant_chunk_ids if chunk_id not in fixture_by_id})
    if missing:
        raise SystemExit(f"evaluation fixture missing relevant chunks: {missing}")

    provider = MockEmbeddingProvider(dimension=settings.embedding_dimension)
    async with SessionLocal() as db:
        owner = (await db.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))).scalar_one_or_none()
        if owner is None:
            raise SystemExit("evaluation runner requires at least one user in the database")
        owner = uuid.UUID(str(owner))
        await prepare_fixture(db, fixtures, owner)
        try:
            fixture_embeddings = await provider.embed([row["content"] for row in fixtures])
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
            vector_provider = PgVectorRetrievalProvider(db, settings.embedding_dimension)
            await vector_provider.upsert(records)

            query_embeddings = await provider.embed([case.query for case in dataset.cases])
            observations: list[RetrievalEvaluationObservation] = []
            case_reports: list[dict[str, object]] = []
            for case, query_embedding in zip(dataset.cases, query_embeddings, strict=True):
                started = time.perf_counter()
                error = None
                ranking: list[str] = []
                try:
                    results = await vector_provider.search(
                        query_embedding,
                        top_k=k,
                        min_score=0.0,
                        knowledge_base_id=str(KB_ID),
                    )
                    ranking = [result.metadata.get("evaluation_chunk_id", result.chunk_id) for result in results]
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                latency_ms = round((time.perf_counter() - started) * 1000, 3)
                observations.append(RetrievalEvaluationObservation(
                    retrieved_chunk_ids=tuple(ranking), latency_ms=latency_ms, error=error
                ))
                case_reports.append({
                    "query": case.query,
                    "relevant_chunk_ids": sorted(case.relevant_chunk_ids),
                    "retrieved_chunk_ids": ranking,
                    "latency_ms": latency_ms,
                    "error": error,
                })

            metrics = aggregate_observations(dataset.cases, observations, k=k)
            baseline_all = json.loads(BASELINE.read_text(encoding="utf-8"))
            baseline = baseline_all.get("mock-pgvector", {})
            failures = quality_gate(metrics, baseline)
            report = {
                "dataset": {"path": str(dataset.source), "schema_version": dataset.schema_version},
                "mode": "mock-pgvector",
                "source": "postgresql/pgvector",
                "k": k,
                **metrics,
                "cases_detail": case_reports,
                "quality_gate": "failed" if failures else "passed",
                "failures": failures,
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if failures else 0
        finally:
            await cleanup_fixture(db)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Knowledge Retrieval directly against PostgreSQL/pgvector using deterministic mock embeddings"
    )
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if args.k < 1:
        raise SystemExit("--k must be greater than zero")
    return asyncio.run(run(args.k))


if __name__ == "__main__":
    raise SystemExit(main())
