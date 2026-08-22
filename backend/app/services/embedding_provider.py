from __future__ import annotations

from typing import Sequence

import httpx


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider returns an invalid or failed response."""


class OpenAICompatibleEmbeddingProvider:
    """Embedding adapter for providers exposing an OpenAI-compatible /embeddings API.

    ``expected_dimension`` is the application/provider contract. The provider
    still validates the actual vector length returned by the remote model so a
    configuration typo cannot silently corrupt the vector store.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
        dimensions: int | None = None,
        expected_dimension: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.dimensions = dimensions
        self.expected_dimension = expected_dimension
        self.dimension: int | None = expected_dimension
        self._client = client
        if expected_dimension is not None and expected_dimension < 1:
            raise EmbeddingProviderError("embedding dimensions must be greater than zero")

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise EmbeddingProviderError("embedding texts must not contain empty values")

        payload: dict[str, object] = {"model": self.model, "input": list(texts)}
        if self.dimensions is not None:
            if self.dimensions < 1:
                raise EmbeddingProviderError("embedding dimensions must be greater than zero")
            payload["dimensions"] = self.dimensions
        headers = {"Authorization": f"Bearer {self.api_key}"}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EmbeddingProviderError("embedding provider request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingProviderError("embedding provider returned an invalid data length")

        ordered: list[tuple[int, list[float]]] = []
        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingProviderError("embedding provider returned an invalid item")
            index = item.get("index")
            embedding = item.get("embedding")
            if not isinstance(index, int) or not isinstance(embedding, list):
                raise EmbeddingProviderError("embedding provider returned an invalid embedding item")
            if not all(isinstance(value, (int, float)) for value in embedding):
                raise EmbeddingProviderError("embedding vector contains a non-numeric value")
            ordered.append((index, [float(value) for value in embedding]))

        ordered.sort(key=lambda item: item[0])
        if [index for index, _ in ordered] != list(range(len(texts))):
            raise EmbeddingProviderError("embedding provider returned non-contiguous indexes")

        embeddings = [embedding for _, embedding in ordered]
        actual_dimensions = {len(embedding) for embedding in embeddings}
        if len(actual_dimensions) != 1:
            raise EmbeddingProviderError("embedding provider returned inconsistent dimensions")
        actual_dimension = actual_dimensions.pop()
        if actual_dimension < 1:
            raise EmbeddingProviderError("embedding provider returned an empty vector")
        if self.expected_dimension is not None and actual_dimension != self.expected_dimension:
            raise EmbeddingProviderError(
                f"embedding dimensions {actual_dimension} do not match configured dimension "
                f"{self.expected_dimension}"
            )
        self.dimension = actual_dimension
        return embeddings
