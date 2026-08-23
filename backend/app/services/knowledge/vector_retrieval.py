from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion
from app.services.embedding_provider import EmbeddingProvider, EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from app.services.knowledge.retrieval import KnowledgeRetrievalService
from app.services.mock_embedding_provider import MockEmbeddingProvider
from app.services.ollama_embedding_provider import OllamaEmbeddingProvider
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRetrievalProviderError


class VectorKnowledgeRetrievalService:
    RETRIEVAL_MODE = "vector"

    def __init__(self, db: AsyncSession, *, embedding_provider: EmbeddingProvider | None = None, embedding_dimension: int | None = None):
        self.db = db
        self._embedding_provider = embedding_provider
        self._embedding_dimension = embedding_dimension

    @staticmethod
    def _build_embedding_provider():
        if settings.embedding_provider == "mock":
            return MockEmbeddingProvider(dimension=settings.embedding_dimension)
        common = {"model": settings.embedding_model, "timeout_seconds": settings.embedding_timeout_seconds, "expected_dimension": settings.embedding_dimension}
        if settings.embedding_provider == "ollama":
            return OllamaEmbeddingProvider(base_url=settings.embedding_base_url, **common)
        return OpenAICompatibleEmbeddingProvider(base_url=settings.embedding_base_url, api_key=settings.embedding_api_key, **common)

    async def retrieve(self, query: str, top_k: int, owner_id: UUID, is_admin: bool = False, knowledge_base_id: UUID | None = None, document_id: UUID | None = None, min_score: float = 0.0, dedupe: bool = True) -> list[dict]:
        if not query.strip():
            raise HTTPException(status_code=422, detail="query 不能为空")
        if settings.vector_provider != "pgvector":
            raise HTTPException(status_code=503, detail="VECTOR_PROVIDER=pgvector is required for vector retrieval")
        provider_name = settings.embedding_provider
        if self._embedding_provider is not None:
            provider_name = "explicit"
        elif provider_name not in {"openai-compatible", "ollama", "mock"}:
            raise HTTPException(status_code=503, detail="VECTOR retrieval requires EMBEDDING_PROVIDER=openai-compatible, ollama or mock")
        if self._embedding_provider is None and provider_name in {"openai-compatible", "ollama"} and (not settings.embedding_base_url or not settings.embedding_model):
            raise HTTPException(status_code=503, detail="EMBEDDING_BASE_URL and EMBEDDING_MODEL are required")
        if self._embedding_provider is None and provider_name == "openai-compatible" and not settings.embedding_api_key:
            raise HTTPException(status_code=503, detail="EMBEDDING_API_KEY is required for openai-compatible")
        embedding_dimension = self._embedding_dimension or settings.embedding_dimension
        try:
            embedding_provider = self._embedding_provider or self._build_embedding_provider()
            embeddings = await embedding_provider.embed([query])
            if len(embeddings) != 1:
                raise EmbeddingProviderError("embedding provider returned an invalid query embedding")
            vector_provider = PgVectorRetrievalProvider(self.db, embedding_dimension)
            vector_results = await vector_provider.search(query_embedding=embeddings[0], top_k=top_k, min_score=min_score, knowledge_base_id=str(knowledge_base_id) if knowledge_base_id else None)
        except (EmbeddingProviderError, VectorRetrievalProviderError) as exc:
            raise HTTPException(status_code=503, detail=f"vector retrieval unavailable: {exc}") from exc
        if not vector_results:
            return []
        chunk_ids = [UUID(result.chunk_id) for result in vector_results]
        stmt = (select(KnowledgeDocumentChunk, KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeBase).join(KnowledgeDocumentVersion, KnowledgeDocumentVersion.id == KnowledgeDocumentChunk.document_version_id).join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id).join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id).where(KnowledgeDocumentChunk.id.in_(chunk_ids), KnowledgeDocument.status == "active", KnowledgeDocumentVersion.ingestion_status == "ready", KnowledgeDocumentVersion.status == "ready", KnowledgeDocumentVersion.vector_index_status == "ready"))
        if knowledge_base_id:
            stmt = stmt.where(KnowledgeBase.id == knowledge_base_id)
        if document_id:
            stmt = stmt.where(KnowledgeDocument.id == document_id)
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        rows = (await self.db.execute(stmt)).all()
        by_chunk_id = {str(chunk.id): (chunk, document, version) for chunk, document, version, _ in rows}
        scored = []
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
            scored.append({"document_id": document.id, "document_version_id": version.id, "chunk_id": chunk.id, "chunk_index": chunk.chunk_index, "source_document": document.title, "source_uri": document.source_uri or version.source_uri, "relevance_score": result.score, "citation": f"{document.title}#{chunk.chunk_index}", "content": chunk.content, "matched_terms": [], "retrieval_mode": self.RETRIEVAL_MODE})
        return scored[:top_k]


class KnowledgeRetrievalRouterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(self, *, mode: str, fallback_to_lexical: bool, **kwargs) -> tuple[list[dict], str, bool]:
        if mode == "lexical-v2":
            return await KnowledgeRetrievalService(self.db).retrieve(**kwargs), "lexical-v2", False
        if mode != "vector":
            raise HTTPException(status_code=422, detail=f"unsupported retrieval mode: {mode}")
        try:
            return await VectorKnowledgeRetrievalService(self.db).retrieve(**kwargs), "vector", False
        except HTTPException:
            if not fallback_to_lexical:
                raise
            return await KnowledgeRetrievalService(self.db).retrieve(**kwargs), "lexical-v2", True
