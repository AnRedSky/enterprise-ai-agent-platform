from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.providers.vector_retrieval import PgVectorRetrievalProvider, VectorRecord


@pytest.mark.asyncio
async def test_pgvector_evaluation_upsert_uses_variable_dimension_storage():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    provider = PgVectorRetrievalProvider(db, embedding_dimension=1024)

    await provider.upsert(
        [
            VectorRecord(
                "chunk-a",
                tuple(float(i) for i in range(1024)),
                {
                    "knowledge_base_id": "00000000-0000-0000-0000-000000000101",
                    "document_version_id": "00000000-0000-0000-0000-000000000103",
                    "evaluation_chunk_id": "chunk-fastapi-runtime",
                },
            )
        ]
    )

    sql = str(db.execute.await_args_list[0].args[0])
    assert "retrieval_evaluation_vectors" in sql
    assert "embedding_dimension" in sql
    assert "knowledge_chunks" not in sql
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_pgvector_evaluation_search_is_dimension_scoped():
    db = MagicMock()
    exists_result = MagicMock()
    exists_result.scalar.return_value = True
    search_result = MagicMock()
    search_result.fetchall.return_value = []
    db.execute = AsyncMock(side_effect=[exists_result, search_result])
    provider = PgVectorRetrievalProvider(db, embedding_dimension=1024)

    await provider.search(
        tuple(float(i) for i in range(1024)),
        top_k=3,
        knowledge_base_id="00000000-0000-0000-0000-000000000101",
    )

    sql = str(db.execute.await_args_list[1].args[0])
    params = db.execute.await_args_list[1].args[1]
    assert "retrieval_evaluation_vectors" in sql
    assert "embedding_dimension = :embedding_dimension" in sql
    assert params["embedding_dimension"] == 1024
