"""Ollama Embedding 技术适配器。

职责：负责 Ollama ``/api/embed`` HTTP 调用、有限重试和向量维度校验。
边界：只负责 Ollama 技术协议适配，不包含 Knowledge 领域业务规则或 Provider 路由治理。
关键依赖：httpx、asyncio，以及统一 EmbeddingProviderError。
"""

from __future__ import annotations

import asyncio
from typing import Sequence
from urllib.parse import urlparse

import httpx

from .embedding import EmbeddingProviderError


class OllamaEmbeddingProvider:
    """Ollama Embedding Provider 的统一技术适配器。"""

    _RETRYABLE_STATUS_CODES = frozenset({502, 503, 504})

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        expected_dimension: int | None = None,
        dimensions: int | None = None,
        retry_attempts: int = 5,
        retry_backoff_seconds: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.expected_dimension = expected_dimension
        self.dimensions = dimensions
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self.dimension: int | None = expected_dimension
        self._client = client
        if expected_dimension is not None and expected_dimension < 1:
            raise EmbeddingProviderError("embedding dimensions must be greater than zero")
        if retry_attempts < 0:
            raise EmbeddingProviderError("embedding retry attempts must not be negative")
        if retry_backoff_seconds < 0:
            raise EmbeddingProviderError("embedding retry backoff must not be negative")

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
        client = self._client or self._create_client()
        try:
            response = await self._post_with_retry(client, payload)
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError):
                body = exc.response.text[:300].strip()
                detail = f" (HTTP {exc.response.status_code}: {body})"
                if exc.response.status_code in self._RETRYABLE_STATUS_CODES:
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
        if not all(isinstance(value, (int, float)) for embedding in embeddings for value in embedding):
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

    def _create_client(self) -> None:
        """为本地 Ollama 禁用环境代理，避免 Docker 请求被代理拦截。"""
        hostname = urlparse(self.base_url).hostname
        trust_env = hostname not in {"localhost", "127.0.0.1", "::1"}
        return httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=trust_env)

    async def _post_with_retry(self, client: httpx.AsyncClient, payload: dict[str, object]) -> httpx.Response:
        """对临时 HTTP/网络错误执行有限指数退避重试。"""
        for attempt in range(self.retry_attempts + 1):
            try:
                response = await client.post(f"{self.base_url}/api/embed", json=payload)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in self._RETRYABLE_STATUS_CODES:
                    raise
                if attempt >= self.retry_attempts:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * (2**attempt))
            except httpx.RequestError:
                if attempt >= self.retry_attempts:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * (2**attempt))
        raise RuntimeError("unreachable Ollama embedding retry state")
