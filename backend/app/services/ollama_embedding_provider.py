from __future__ import annotations

from typing import Sequence

import httpx

from app.services.embedding_provider import EmbeddingProviderError


class OllamaEmbeddingProvider:
    """Native Ollama embedding adapter with the same dimension contract."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        expected_dimension: int | None = None,
        dimensions: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.expected_dimension = expected_dimension
        self.dimensions = dimensions
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

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.post(f"{self.base_url}/api/embed", json=payload)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError):
                body = exc.response.text[:300].strip()
                detail = f" (HTTP {exc.response.status_code}: {body})"
                if exc.response.status_code in {502, 503, 504}:
                    detail += (
                        f"; Ollama model '{self.model}' is unavailable at the embedding endpoint; "
                        "check the Ollama container logs and model runner/resource state"
                    )
            raise EmbeddingProviderError(
                f"Ollama embedding request failed for model '{self.model}'{detail}"
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        embeddings = body.get("embeddings") if isinstance(body, dict) else None
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingProviderError("Ollama embedding provider returned an invalid data length")
        if not all(isinstance(item, list) for item in embeddings):
            raise EmbeddingProviderError("Ollama embedding provider returned an invalid embedding item")
        if not all(
            isinstance(value, (int, float))
            for embedding in embeddings
            for value in embedding
        ):
            raise EmbeddingProviderError("embedding vector contains a non-numeric value")

        vectors = [[float(value) for value in embedding] for embedding in embeddings]
        actual_dimensions = {len(embedding) for embedding in vectors}
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
        return vectors
