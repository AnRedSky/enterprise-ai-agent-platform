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
async def test_mock_embedding_provider_matches_chinese_query_inside_longer_chunk() -> None:
    provider = MockEmbeddingProvider(dimension=1536)

    vectors = await provider.embed(
        [
            "报销规则",
            "报销规则规定员工报销的申请条件、金额限制、票据要求以及审批流程。",
            "PostgreSQL 知识库用于保存企业知识文档、文档版本、Chunk 以及检索索引信息。",
        ]
    )

    relevant = sum(a * b for a, b in zip(vectors[0], vectors[1]))
    unrelated = sum(a * b for a, b in zip(vectors[0], vectors[2]))

    assert relevant > unrelated


@pytest.mark.asyncio
async def test_mock_embedding_provider_rejects_blank_text() -> None:
    provider = MockEmbeddingProvider(dimension=16)

    with pytest.raises(EmbeddingProviderError, match="empty values"):
        await provider.embed([" "])
