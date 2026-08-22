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
async def test_ollama_embedding_provider_retries_transient_503() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "model runner unavailable"})
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
        expected_dimension=2,
        retry_attempts=1,
        retry_backoff_seconds=0,
        client=client,
    )
    try:
        assert await provider.embed(["first"]) == [[0.1, 0.2]]
        assert attempts == 2
    finally:
        await client.aclose()


def test_ollama_embedding_provider_default_retry_budget_covers_slow_runner_start() -> None:
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
    )
    assert provider.retry_attempts == 5
    assert provider.retry_backoff_seconds == 1.0


@pytest.mark.asyncio
async def test_ollama_embedding_provider_retries_until_runner_is_ready() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 5:
            return httpx.Response(503, json={"error": "model runner unavailable"})
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
        expected_dimension=2,
        retry_attempts=4,
        retry_backoff_seconds=0,
        client=client,
    )
    try:
        assert await provider.embed(["first"]) == [[0.1, 0.2]]
        assert attempts == 5
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
        retry_attempts=0,
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


@pytest.mark.parametrize(
    "retry_attempts,retry_backoff_seconds,message",
    [
        (-1, 0, "embedding retry attempts must not be negative"),
        (0, -1, "embedding retry backoff must not be negative"),
    ],
)
def test_ollama_embedding_provider_rejects_invalid_retry_configuration(
    retry_attempts: int,
    retry_backoff_seconds: float,
    message: str,
) -> None:
    with pytest.raises(EmbeddingProviderError, match=message):
        OllamaEmbeddingProvider(
            base_url="http://localhost:11434",
            model="nomic-embed-text:latest",
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
