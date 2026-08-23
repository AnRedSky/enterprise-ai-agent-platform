"""Knowledge 领域契约。

只定义检索领域的稳定业务接口；外部 Embedding 技术契约统一由 infrastructure/providers 提供，避免重复定义。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence
from uuid import UUID

from app.infrastructure.providers.embedding import EmbeddingProvider


@dataclass(frozen=True)
class RetrievalCandidate:
    """检索结果的领域中立表示，供排序、引用与 API 层复用。"""

    document_id: UUID
    document_version_id: UUID
    chunk_id: UUID
    chunk_index: int
    source_document: str
    source_uri: str | None
    content: str
    relevance_score: float
    citation: str


class Retriever(Protocol):
    """Knowledge 检索实现的业务契约。"""

    async def retrieve(self, query: str, top_k: int, **filters: object) -> list[RetrievalCandidate]: ...


class Reranker(Protocol):
    """可选重排器的业务契约。"""

    async def rerank(self, query: str, candidates: Sequence[RetrievalCandidate], top_k: int) -> list[RetrievalCandidate]: ...


__all__ = ["EmbeddingProvider", "RetrievalCandidate", "Retriever", "Reranker"]
