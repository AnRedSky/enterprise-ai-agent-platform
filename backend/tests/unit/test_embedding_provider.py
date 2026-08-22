import httpx
import pytest

from app.services.embedding_provider import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_orders_vectors_by_index() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert request.headers["authorization"] == "Bearer test-key"
        payload = request.read()
        assert b'"model":"text-embedding-test"' in payload
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [2, 3]},
                    {"index": 0, "embedding": [0, 1]},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embedding.local/v1",
        api_key="test-key",
        model="text-embedding-test",
        expected_dimension=2,
        client=client,
    )
    try:
        assert await provider.embed(["first", "second"]) == [[0.0, 1.0], [2.0, 3.0]]
        assert provider.dimension == 2
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_can_request_output_dimensions() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        assert b'"model":"qwen3-embedding:4b"' in body
        assert b'"dimensions":1536' in body
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="qwen3-embedding:4b",
        dimensions=1536,
        expected_dimension=2,
        client=client,
    )
    try:
        assert await provider.embed(["local ollama"]) == [[0.1, 0.2]]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_rejects_dimension_mismatch() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
            )
        )
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embedding.local/v1",
        api_key="test-key",
        model="text-embedding-test",
        expected_dimension=3,
        client=client,
    )
    try:
        with pytest.raises(EmbeddingProviderError, match="do not match configured dimension 3"):
            await provider.embed(["first"])
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_rejects_inconsistent_batch_dimensions() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "data": [
                        {"index": 0, "embedding": [0.1, 0.2]},
                        {"index": 1, "embedding": [0.1, 0.2, 0.3]},
                    ]
                },
            )
        )
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embedding.local/v1",
        api_key="test-key",
        model="text-embedding-test",
        client=client,
    )
    try:
        with pytest.raises(EmbeddingProviderError, match="inconsistent dimensions"):
            await provider.embed(["first", "second"])
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_rejects_invalid_response() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": []}))
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embedding.local/v1",
        api_key="test-key",
        model="text-embedding-test",
        client=client,
    )
    try:
        with pytest.raises(EmbeddingProviderError, match="invalid data length"):
            await provider.embed(["first"])
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_rejects_http_errors() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(503, json={"error": "unavailable"}))
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embedding.local/v1",
        api_key="test-key",
        model="text-embedding-test",
        client=client,
    )
    try:
        with pytest.raises(EmbeddingProviderError, match="request failed"):
            await provider.embed(["first"])
    finally:
        await client.aclose()
