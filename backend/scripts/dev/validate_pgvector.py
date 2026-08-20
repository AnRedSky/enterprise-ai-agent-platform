from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

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
    user_id = "00000000-0000-0000-0000-000000000001"
    kb_id = "00000000-0000-0000-0000-000000000002"
    document_id = "00000000-0000-0000-0000-000000000003"
    version_id = "00000000-0000-0000-0000-000000000004"
    chunk_id = "00000000-0000-0000-0000-000000000005"

    try:
        async with AsyncSession(engine) as session:
            extension = await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            if extension.scalar_one_or_none() != "vector":
                raise VectorRetrievalProviderError("PostgreSQL extension 'vector' is not installed")

            table = await session.execute(text("SELECT to_regclass('public.knowledge_chunks')"))
            if table.scalar_one_or_none() != "knowledge_chunks":
                raise VectorRetrievalProviderError(
                    "knowledge_chunks table does not exist; run uv run alembic upgrade head"
                )

            await session.execute(
                text(
                    """
                    INSERT INTO users (id, username, password_hash, status, created_at)
                    VALUES (CAST(:id AS uuid), 'pgvector-validation-probe', 'probe', 'active', CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": user_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_bases
                        (id, name, description, owner_id, status, created_at, updated_at)
                    VALUES
                        (CAST(:id AS uuid), 'pgvector probe', '', CAST(:user_id AS uuid), 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": kb_id, "user_id": user_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_documents
                        (id, knowledge_base_id, title, source_type, status, created_at, updated_at)
                    VALUES
                        (CAST(:id AS uuid), CAST(:kb_id AS uuid), 'pgvector probe', 'manual', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": document_id, "kb_id": kb_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_document_versions
                        (id, document_id, version, status, ingestion_status, created_by, created_at)
                    VALUES
                        (CAST(:id AS uuid), CAST(:document_id AS uuid), 'probe', 'ready', 'completed', CAST(:user_id AS uuid), CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": version_id, "document_id": document_id, "user_id": user_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_document_chunks
                        (id, document_version_id, chunk_index, content, char_start, char_end, content_hash, token_count, created_at)
                    VALUES
                        (CAST(:id AS uuid), CAST(:version_id AS uuid), 999999, 'pgvector validation probe', 0, 25, 'pgvector-probe', 4, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": chunk_id, "version_id": version_id},
            )
            await session.commit()

            provider = PgVectorRetrievalProvider(
                session,
                embedding_dimension=settings.embedding_dimension,
            )
            vector = tuple([1.0] + [0.0] * (settings.embedding_dimension - 1))
            await provider.upsert(
                [
                    VectorRecord(
                        chunk_id,
                        vector,
                        {
                            "knowledge_base_id": kb_id,
                            "document_version_id": version_id,
                            "source": "validation",
                        },
                    )
                ]
            )
            results = await provider.search(vector, top_k=1, min_score=0.99, knowledge_base_id=kb_id)
            if not results or results[0].chunk_id != chunk_id or results[0].score < 0.99:
                raise VectorRetrievalProviderError("pgvector upsert/search round-trip failed")

            await session.execute(
                text("DELETE FROM knowledge_document_chunks WHERE id = CAST(:id AS uuid)"),
                {"id": chunk_id},
            )
            await session.execute(
                text("DELETE FROM knowledge_document_versions WHERE id = CAST(:id AS uuid)"),
                {"id": version_id},
            )
            await session.execute(
                text("DELETE FROM knowledge_documents WHERE id = CAST(:id AS uuid)"),
                {"id": document_id},
            )
            await session.execute(
                text("DELETE FROM knowledge_bases WHERE id = CAST(:id AS uuid)"),
                {"id": kb_id},
            )
            await session.execute(
                text("DELETE FROM users WHERE id = CAST(:id AS uuid)"),
                {"id": user_id},
            )
            await session.commit()

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
