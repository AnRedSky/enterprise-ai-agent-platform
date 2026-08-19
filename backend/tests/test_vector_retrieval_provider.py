import pytest

from app.services.vector_retrieval_provider import (
    InMemoryVectorRetrievalProvider,
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
async def test_in_memory_vector_provider_applies_min_score_and_stable_ties() -> None:
    provider = InMemoryVectorRetrievalProvider()
    await provider.upsert(
        [
            VectorRecord("chunk-b", (1.0, 0.0), {}),
            VectorRecord("chunk-a", (1.0, 0.0), {}),
            VectorRecord("chunk-c", (0.0, 1.0), {}),
        ]
    )

    results = await provider.search((1.0, 0.0), top_k=10, min_score=0.99)

    assert [item.chunk_id for item in results] == ["chunk-a", "chunk-b"]


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
