from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion
from app.services.embedding_provider import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from app.services.knowledge_retrieval import KnowledgeRetrievalService
from app.services.mock_embedding_provider import MockEmbeddingProvider
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRetrievalProviderError


class VectorKnowledgeRetrievalService:
    """Query embedding + PostgreSQL/pgvector search + authorized chunk hydration.

    ``mock`` embeddings are intentionally supported for local deterministic
    database-loop validation. They exercise the same PostgreSQL/pgvector
    indexing/search path as a real embedding provider; they must not be used as
    evidence of real model semantic quality.
    """

    RETRIEVAL_MODE = "vector"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        top_k: int,
        owner_id: UUID,
        is_admin: bool = False,
        knowledge_base_id: UUID | None = None,
        document_id: UUID | None = None,
        min_score: float = 0.0,
        dedupe: bool = True,
    ) -> list[dict]:
        if not query.strip():
            raise HTTPException(status_code=422, detail="query 不能为空")
        if settings.vector_provider != "pgvector":
            raise HTTPException(status_code=503, detail="VECTOR_PROVIDER=pgvector is required for vector retrieval")
        if settings.embedding_provider not in {"openai-compatible", "mock"}:
            raise HTTPException(
                status_code=503,
                detail="VECTOR retrieval requires EMBEDDING_PROVIDER=openai-compatible or mock",
            )
        if settings.embedding_provider == "openai-compatible" and (
            not settings.embedding_base_url or not settings.embedding_api_key or not settings.embedding_model
        ):
            raise HTTPException(status_code=503, detail="EMBEDDING_BASE_URL, EMBEDDING_API_KEY and EMBEDDING_MODEL are required")

        try:
            if settings.embedding_provider == "mock":
                embedding_provider = MockEmbeddingProvider(dimension=settings.embedding_dimension)
            else:
                embedding_provider = OpenAICompatibleEmbeddingProvider(
                    base_url=settings.embedding_base_url,
                    api_key=settings.embedding_api_key,
                    model=settings.embedding_model,
                    timeout_seconds=settings.embedding_timeout_seconds,
                )
            embeddings = await embedding_provider.embed([query])
            if len(embeddings) != 1:
                raise EmbeddingProviderError("embedding provider returned an invalid query embedding")

            vector_provider = PgVectorRetrievalProvider(self.db, settings.embedding_dimension)
            vector_results = await vector_provider.search(
                query_embedding=embeddings[0],
                top_k=top_k,
                min_score=min_score,
                knowledge_base_id=str(knowledge_base_id) if knowledge_base_id else None,
            )
        except (EmbeddingProviderError, VectorRetrievalProviderError) as exc:
            raise HTTPException(status_code=503, detail=f"vector retrieval unavailable: {exc}") from exc

        if not vector_results:
            return []

        chunk_ids = [UUID(result.chunk_id) for result in vector_results]
        stmt = (
            select(KnowledgeDocumentChunk, KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeBase)
            .join(KnowledgeDocumentVersion, KnowledgeDocumentVersion.id == KnowledgeDocumentChunk.document_version_id)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
            .where(
                KnowledgeDocumentChunk.id.in_(chunk_ids),
                KnowledgeDocument.status == "active",
                KnowledgeDocumentVersion.ingestion_status == "ready",
                KnowledgeDocumentVersion.status == "ready",
                KnowledgeDocumentVersion.vector_index_status == "ready",
            )
        )
        if knowledge_base_id:
            stmt = stmt.where(KnowledgeBase.id == knowledge_base_id)
        if document_id:
            stmt = stmt.where(KnowledgeDocument.id == document_id)
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)

        rows = (await self.db.execute(stmt)).all()
        by_chunk_id = {str(chunk.id): (chunk, document, version) for chunk, document, version, _ in rows}
        scored: list[dict] = []
        seen_content: set[str] = set()
        for result in vector_results:
            hydrated = by_chunk_id.get(result.chunk_id)
            if hydrated is None:
                continue
            chunk, document, version = hydrated
            content_key = chunk.content_hash or chunk.content
            if dedupe and content_key in seen_content:
                continue
            seen_content.add(content_key)
            scored.append(
                {
                    "document_id": document.id,
                    "document_version_id": version.id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "source_document": document.title,
                    "source_uri": document.source_uri or version.source_uri,
                    "relevance_score": result.score,
                    "citation": f"{document.title}#{chunk.chunk_index}",
                    "content": chunk.content,
                    "matched_terms": [],
                    "retrieval_mode": self.RETRIEVAL_MODE,
                }
            )
        return scored[:top_k]


class KnowledgeRetrievalRouterService:
    """Keep mode selection and explicit degradation policy in one place."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(self, *, mode: str, fallback_to_lexical: bool, **kwargs) -> tuple[list[dict], str, bool]:
        if mode == "lexical-v2":
            results = await KnowledgeRetrievalService(self.db).retrieve(**kwargs)
            return results, "lexical-v2", False
        if mode != "vector":
            raise HTTPException(status_code=422, detail=f"unsupported retrieval mode: {mode}")

        try:
            results = await VectorKnowledgeRetrievalService(self.db).retrieve(**kwargs)
            return results, "vector", False
        except HTTPException:
            if not fallback_to_lexical:
                raise
            results = await KnowledgeRetrievalService(self.db).retrieve(**kwargs)
            return results, "lexical-v2", True
