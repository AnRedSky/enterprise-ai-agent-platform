import httpx
import pytest

from app.services.embedding_provider import EmbeddingProviderError
from app.services.ollama_embedding_provider import OllamaEmbeddingProvider


@pytest.mark.asyncio
async def test_ollama_embedding_provider_uses_native_embed_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        body = request.read()
        assert b'"model":"nomic-embed-text:latest"' in body
        return httpx.Response(
            200,
            json={"model": "nomic-embed-text:latest", "embeddings": [[0.1, 0.2], [0.3, 0.4]]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
        expected_dimension=2,
        client=client,
    )
    try:
        assert await provider.embed(["first", "second"]) == [[0.1, 0.2], [0.3, 0.4]]
        assert provider.dimension == 2
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ollama_embedding_provider_rejects_dimension_mismatch() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})
        )
    )
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
        expected_dimension=3,
        client=client,
    )
    try:
        with pytest.raises(EmbeddingProviderError, match="do not match configured dimension 3"):
            await provider.embed(["first"])
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ollama_embedding_provider_reports_http_error_body() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(500, json={"error": "model not found"})
        )
    )
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="missing-model",
        client=client,
    )
    try:
        with pytest.raises(EmbeddingProviderError, match="HTTP 500"):
            await provider.embed(["first"])
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ollama_embedding_provider_adds_runtime_diagnostic_for_503() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(503, json={"error": "model runner unavailable"})
        )
    )
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
        client=client,
    )
    try:
        with pytest.raises(
            EmbeddingProviderError,
            match="Ollama model 'nomic-embed-text:latest'.*container logs.*resource state",
        ):
            await provider.embed(["first"])
    finally:
        await client.aclose()
