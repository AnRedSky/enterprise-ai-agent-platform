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

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.dependencies.db import SessionLocal
from app.services.mock_embedding_provider import MockEmbeddingProvider
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRecord

DATASET = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_dataset.jsonl"
FIXTURE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_fixture.jsonl"
RESULTS = BACKEND_ROOT / "evaluation" / "vector_results.jsonl"
FIXTURE_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000100")
KB_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
DOC_ID = uuid.UUID("00000000-0000-0000-0000-000000000102")
VERSION_ID = uuid.UUID("00000000-0000-0000-0000-000000000103")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def actual_chunk_id(evaluation_chunk_id: str) -> uuid.UUID:
    return uuid.uuid5(FIXTURE_NAMESPACE, evaluation_chunk_id)


async def prepare_fixture(db, rows: list[dict], user_id: uuid.UUID) -> None:
    await db.execute(text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :kb"), {"kb": str(KB_ID)})
    await db.execute(text("DELETE FROM knowledge_document_chunks WHERE document_version_id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_document_versions WHERE id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_documents WHERE id = :doc"), {"doc": str(DOC_ID)})
    await db.execute(text("DELETE FROM knowledge_bases WHERE id = :kb"), {"kb": str(KB_ID)})

    await db.execute(
        text("""
            INSERT INTO knowledge_bases
                (id, name, description, owner_id, status, created_at, updated_at)
            VALUES
                (:id, 'Phase 1.4-E Evaluation Fixture',
                 'Ephemeral deterministic retrieval evaluation data',
                 :owner, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {"id": str(KB_ID), "owner": str(user_id)},
    )
    await db.execute(
        text("""
            INSERT INTO knowledge_documents
                (id, knowledge_base_id, title, source_type, status, created_at, updated_at)
            VALUES
                (:id, :kb, 'Phase 1.4-E Evaluation Fixture', 'evaluation', 'active',
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {"id": str(DOC_ID), "kb": str(KB_ID)},
    )
    await db.execute(
        text("""
            INSERT INTO knowledge_document_versions
                (id, document_id, version, status, ingestion_status, vector_index_status, created_by, created_at)
            VALUES
                (:id, :doc, 'evaluation', 'published', 'completed', 'processing', :user, CURRENT_TIMESTAMP)
        """),
        {"id": str(VERSION_ID), "doc": str(DOC_ID), "user": str(user_id)},
    )
    for index, row in enumerate(rows):
        chunk_id = actual_chunk_id(row["chunk_id"])
        content = row["content"]
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        await db.execute(
            text("""
                INSERT INTO knowledge_document_chunks
                    (id, document_version_id, chunk_index, content, char_start, char_end,
                     content_hash, token_count, created_at)
                VALUES
                    (:id, :version, :index, :content, 0, :char_end, :hash, :tokens, CURRENT_TIMESTAMP)
            """),
            {
                "id": str(chunk_id),
                "version": str(VERSION_ID),
                "index": index,
                "content": content,
                "char_end": len(content),
                "hash": digest,
                "tokens": len(content.split()),
            },
        )
    await db.execute(
        text("UPDATE knowledge_documents SET current_version_id = :version WHERE id = :doc"),
        {"version": str(VERSION_ID), "doc": str(DOC_ID)},
    )
    await db.commit()


async def cleanup_fixture(db) -> None:
    await db.execute(text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :kb"), {"kb": str(KB_ID)})
    await db.execute(text("DELETE FROM knowledge_document_chunks WHERE document_version_id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_document_versions WHERE id = :version"), {"version": str(VERSION_ID)})
    await db.execute(text("DELETE FROM knowledge_documents WHERE id = :doc"), {"doc": str(DOC_ID)})
    await db.execute(text("DELETE FROM knowledge_bases WHERE id = :kb"), {"kb": str(KB_ID)})
    await db.commit()


async def run(k: int) -> None:
    if settings.embedding_provider != "mock":
        raise SystemExit("Evaluation runner requires EMBEDDING_PROVIDER=mock for offline validation")
    if settings.vector_provider != "pgvector":
        raise SystemExit("Evaluation runner requires VECTOR_PROVIDER=pgvector")

    cases = load_jsonl(DATASET)
    fixtures = load_jsonl(FIXTURE)
    fixture_by_id = {row["chunk_id"]: row for row in fixtures}
    missing = sorted({chunk_id for case in cases for chunk_id in case["relevant_chunk_ids"] if chunk_id not in fixture_by_id})
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
            records = []
            for row, embedding in zip(fixtures, fixture_embeddings, strict=True):
                records.append(
                    VectorRecord(
                        chunk_id=str(actual_chunk_id(row["chunk_id"])),
                        embedding=tuple(embedding),
                        metadata={
                            "knowledge_base_id": str(KB_ID),
                            "document_version_id": str(VERSION_ID),
                            "evaluation_chunk_id": row["chunk_id"],
                        },
                    )
                )
            vector_provider = PgVectorRetrievalProvider(db, settings.embedding_dimension)
            await vector_provider.upsert(records)

            query_embeddings = await provider.embed([case["query"] for case in cases])
            output: list[dict] = []
            for case, query_embedding in zip(cases, query_embeddings, strict=True):
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
                except Exception as exc:  # evaluation output must record provider failures
                    error = f"{type(exc).__name__}: {exc}"
                latency_ms = round((time.perf_counter() - started) * 1000, 3)
                output.append({
                    "query": case["query"],
                    "mode": "mock-pgvector",
                    "ranking": ranking,
                    "latency_ms": latency_ms,
                    "error": error,
                })

            RESULTS.parent.mkdir(parents=True, exist_ok=True)
            RESULTS.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output),
                encoding="utf-8",
            )
            print(f"Generated {len(output)} retrieval observations: {RESULTS}")
        finally:
            await cleanup_fixture(db)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Mock Embedding + PostgreSQL/pgvector retrieval evaluation")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if args.k < 1:
        raise SystemExit("--k must be greater than zero")
    asyncio.run(run(args.k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
