import pytest

from app.services.mock_embedding_provider import MockEmbeddingProvider
from app.services.embedding_provider import EmbeddingProviderError


@pytest.mark.asyncio
async def test_mock_embedding_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider(dimension=32)

    first = await provider.embed(["FastAPI Agent Runtime"])
    second = await provider.embed(["FastAPI Agent Runtime"])

    assert first == second
    assert len(first[0]) == 32
    assert pytest.approx(sum(value * value for value in first[0]), abs=1e-9) == 1.0


@pytest.mark.asyncio
async def test_mock_embedding_provider_preserves_shared_token_similarity() -> None:
    provider = MockEmbeddingProvider(dimension=64)

    vectors = await provider.embed(
        [
            "FastAPI Agent Runtime",
            "FastAPI Agent Runtime execution",
            "expense reimbursement policy",
        ]
    )

    related = sum(a * b for a, b in zip(vectors[0], vectors[1]))
    unrelated = sum(a * b for a, b in zip(vectors[0], vectors[2]))

    assert related > unrelated


@pytest.mark.asyncio
async def test_mock_embedding_provider_rejects_blank_text() -> None:
    provider = MockEmbeddingProvider(dimension=16)

    with pytest.raises(EmbeddingProviderError, match="empty values"):
        await provider.embed([" "])
