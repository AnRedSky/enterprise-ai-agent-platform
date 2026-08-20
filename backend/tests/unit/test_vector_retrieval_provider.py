from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.vector_retrieval_provider import (
    InMemoryVectorRetrievalProvider,
    PgVectorRetrievalProvider,
    VectorRecord,
    VectorRetrievalProviderError,
)


@pytest.mark.asyncio
async def test_in_memory_vector_provider_ranks_by_cosine_similarity() -> None:
    provider = InMemoryVectorRetrievalProvider()
    await provider.upsert(
        [
            VectorRecord("chunk-a", (1.0, 0.0), {"source": "a"}),
            VectorRecord("chunk-b", (0.0, 1.0), {"source": "b"}),
            VectorRecord("chunk-c", (0.8, 0.2), {"source": "c"}),
        ]
    )

    results = await provider.search((1.0, 0.0), top_k=2)

    assert [item.chunk_id for item in results] == ["chunk-a", "chunk-c"]
    assert results[0].score == 1.0
    assert results[1].score > 0.9
    assert results[1].metadata["source"] == "c"


@pytest.mark.asyncio
async def test_in_memory_vector_provider_applies_min_score_and_knowledge_scope() -> None:
    provider = InMemoryVectorRetrievalProvider()
    await provider.upsert(
        [
            VectorRecord("chunk-b", (1.0, 0.0), {"knowledge_base_id": "kb-2"}),
            VectorRecord("chunk-a", (1.0, 0.0), {"knowledge_base_id": "kb-1"}),
            VectorRecord("chunk-c", (0.0, 1.0), {"knowledge_base_id": "kb-1"}),
        ]
    )

    results = await provider.search((1.0, 0.0), top_k=10, min_score=0.99, knowledge_base_id="kb-1")

    assert [item.chunk_id for item in results] == ["chunk-a"]


@pytest.mark.asyncio
async def test_in_memory_vector_provider_rejects_dimension_mismatch() -> None:
    provider = InMemoryVectorRetrievalProvider()
    await provider.upsert([VectorRecord("chunk-a", (1.0, 0.0), {})])

    with pytest.raises(VectorRetrievalProviderError, match="dimensions must match"):
        await provider.search((1.0, 0.0, 0.0), top_k=1)


@pytest.mark.asyncio
async def test_in_memory_vector_provider_rejects_invalid_search_policy() -> None:
    provider = InMemoryVectorRetrievalProvider()

    with pytest.raises(VectorRetrievalProviderError, match="top_k"):
        await provider.search((1.0,), top_k=0)

    with pytest.raises(VectorRetrievalProviderError, match="min_score"):
        await provider.search((1.0,), top_k=1, min_score=1.1)


def test_pgvector_provider_validates_configured_dimension() -> None:
    db = MagicMock()
    provider = PgVectorRetrievalProvider(db, embedding_dimension=3)

    with pytest.raises(VectorRetrievalProviderError, match="configured dimension 3"):
        provider._validate_embedding((1.0, 0.0))


def test_pgvector_provider_builds_vector_literal() -> None:
    assert PgVectorRetrievalProvider._vector_literal((1, 0.25, -0.5)) == "[1.0,0.25,-0.5]"


@pytest.mark.asyncio
async def test_pgvector_provider_requires_scope_metadata() -> None:
    db = MagicMock()
    db.execute = AsyncMock()
    provider = PgVectorRetrievalProvider(db, embedding_dimension=2)

    with pytest.raises(VectorRetrievalProviderError, match="knowledge_base_id"):
        await provider.upsert([VectorRecord("chunk-a", (1.0, 0.0), {})])

    db.execute.assert_not_awaited()
