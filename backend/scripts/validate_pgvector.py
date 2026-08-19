from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.vector_retrieval_provider import (
    PgVectorRetrievalProvider,
    VectorRecord,
    VectorRetrievalProviderError,
)


async def validate() -> int:
    if settings.vector_provider != "pgvector":
        print("pgvector probe skipped: set VECTOR_PROVIDER=pgvector in backend/.env.")
        return 0

    if not settings.vector_db_url:
        print("Missing VECTOR_DB_URL. Set it to the PostgreSQL async connection URL.")
        return 2

    engine = create_async_engine(settings.vector_db_url, pool_pre_ping=True)
    probe_id = "00000000-0000-0000-0000-000000000001"
    kb_id = "00000000-0000-0000-0000-000000000002"
    version_id = "00000000-0000-0000-0000-000000000003"

    try:
        async with engine.begin() as connection:
            extension = await connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            if extension.scalar_one_or_none() != "vector":
                raise VectorRetrievalProviderError("PostgreSQL extension 'vector' is not installed")

            table = await connection.execute(
                text("SELECT to_regclass('public.knowledge_chunks')")
            )
            if table.scalar_one_or_none() != "knowledge_chunks":
                raise VectorRetrievalProviderError("knowledge_chunks table does not exist; run uv run alembic upgrade head")

            provider = PgVectorRetrievalProvider(
                connection,
                embedding_dimension=settings.embedding_dimension,
            )
            vector = tuple([1.0] + [0.0] * (settings.embedding_dimension - 1))
            await connection.execute(
                text(
                    """
                    INSERT INTO knowledge_bases (id, name, description, owner_id, status, created_at, updated_at)
                    SELECT CAST(:kb_id AS uuid), 'pgvector probe', '', id, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM users ORDER BY created_at LIMIT 1
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"kb_id": kb_id},
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO knowledge_document_versions
                        (id, document_id, version, status, ingestion_status, created_by, created_at)
                    SELECT CAST(:version_id AS uuid), d.id, 'probe', 'ready', 'completed', d.owner_id, CURRENT_TIMESTAMP
                    FROM knowledge_documents d
                    JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
                    WHERE kb.id = CAST(:kb_id AS uuid)
                    ORDER BY d.created_at LIMIT 1
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"version_id": version_id, "kb_id": kb_id},
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO knowledge_document_chunks
                        (id, document_version_id, chunk_index, content, char_start, char_end, content_hash, token_count, created_at)
                    VALUES
                        (CAST(:chunk_id AS uuid), CAST(:version_id AS uuid), 999999, 'pgvector validation probe', 0, 25, 'pgvector-probe', 4, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"chunk_id": probe_id, "version_id": version_id},
            )

            await provider.upsert(
                [
                    VectorRecord(
                        probe_id,
                        vector,
                        {"knowledge_base_id": kb_id, "document_version_id": version_id, "source": "validation"},
                    )
                ]
            )
            results = await provider.search(vector, top_k=1, min_score=0.99, knowledge_base_id=kb_id)
            if not results or results[0].chunk_id != probe_id or results[0].score < 0.99:
                raise VectorRetrievalProviderError("pgvector upsert/search round-trip failed")

            await connection.execute(
                text("DELETE FROM knowledge_document_chunks WHERE id = CAST(:chunk_id AS uuid)"),
                {"chunk_id": probe_id},
            )

            print(
                "pgvector validation passed: "
                f"dimension={settings.embedding_dimension}, top_k={settings.vector_top_k}, "
                f"score={results[0].score}"
            )
            return 0
    except VectorRetrievalProviderError as exc:
        print(f"pgvector validation failed: {exc}")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(validate()))
