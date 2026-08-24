"""Knowledge 领域契约。

职责：定义知识检索领域稳定的业务契约与检索结果表示，供知识服务及其适配器复用。
边界：不实现向量检索、Embedding 或 Provider 技术能力；外部技术契约统一复用 infrastructure/providers，避免重复定义。
关键依赖：infrastructure/providers.embedding.EmbeddingProvider。
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
