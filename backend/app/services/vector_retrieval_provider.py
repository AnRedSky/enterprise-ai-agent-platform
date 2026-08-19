from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Protocol, Sequence


class VectorRetrievalProviderError(RuntimeError):
    """Raised when a vector retrieval provider cannot satisfy its contract."""


@dataclass(frozen=True)
class VectorRecord:
    """Provider-neutral vector record used by retrieval adapters."""

    chunk_id: str
    embedding: tuple[float, ...]
    metadata: dict[str, str]


@dataclass(frozen=True)
class VectorSearchResult:
    """Provider-neutral vector search result."""

    chunk_id: str
    score: float
    metadata: dict[str, str]


class VectorRetrievalProvider(Protocol):
    """Contract implemented by pgvector, Milvus, or another vector backend."""

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        ...

    async def search(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        min_score: float = 0.0,
    ) -> list[VectorSearchResult]:
        ...


class InMemoryVectorRetrievalProvider:
    """Deterministic local adapter for contract tests before a real Vector DB."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        for record in records:
            if not record.embedding:
                raise VectorRetrievalProviderError("embedding must not be empty")
            if not all(isinstance(value, (int, float)) for value in record.embedding):
                raise VectorRetrievalProviderError("embedding vector contains a non-numeric value")
            self._records[record.chunk_id] = record

    async def search(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        min_score: float = 0.0,
    ) -> list[VectorSearchResult]:
        if not query_embedding:
            raise VectorRetrievalProviderError("query embedding must not be empty")
        if top_k < 1:
            raise VectorRetrievalProviderError("top_k must be greater than zero")
        if not 0 <= min_score <= 1:
            raise VectorRetrievalProviderError("min_score must be between 0 and 1")

        query = tuple(float(value) for value in query_embedding)
        results: list[VectorSearchResult] = []
        for record in self._records.values():
            if len(record.embedding) != len(query):
                raise VectorRetrievalProviderError("embedding dimensions must match")
            score = self._cosine_similarity(query, record.embedding)
            if score >= min_score:
                results.append(
                    VectorSearchResult(
                        chunk_id=record.chunk_id,
                        score=round(score, 6),
                        metadata=record.metadata,
                    )
                )

        results.sort(key=lambda item: (-item.score, item.chunk_id))
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (left_norm * right_norm)))
