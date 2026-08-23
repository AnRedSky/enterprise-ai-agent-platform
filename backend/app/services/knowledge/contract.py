from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence
from uuid import UUID


@dataclass(frozen=True)
class RetrievalCandidate:
    document_id: UUID
    document_version_id: UUID
    chunk_id: UUID
    chunk_index: int
    source_document: str
    source_uri: str | None
    content: str
    relevance_score: float
    citation: str


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class Retriever(Protocol):
    async def retrieve(self, query: str, top_k: int, **filters: object) -> list[RetrievalCandidate]:
        """Return provider-neutral retrieval candidates."""


class Reranker(Protocol):
    async def rerank(self, query: str, candidates: Sequence[RetrievalCandidate], top_k: int) -> list[RetrievalCandidate]:
        """Optionally reorder retrieval candidates without changing their source metadata."""
