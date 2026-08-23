"""Knowledge 向量索引领域服务。

负责将已持久化 Chunk 转换为向量并交给唯一的 Infrastructure Provider 写入；不实现外部模型或向量数据库协议。
"""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.providers import (
    EmbeddingProviderError,
    MockEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    PgVectorRetrievalProvider,
    VectorRecord,
    VectorRetrievalProviderError,
)
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion


class KnowledgeVectorIndexingService:
    """Build embeddings for persisted chunks and upsert them into the configured vector provider."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def build_records(chunks: Sequence[KnowledgeDocumentChunk], embeddings: Sequence[Sequence[float]], knowledge_base_id: UUID, document_version_id: UUID) -> list[VectorRecord]:
        if len(chunks) != len(embeddings):
            raise VectorRetrievalProviderError("embedding count must match chunk count")
        return [VectorRecord(chunk_id=str(chunk.id), embedding=tuple(float(value) for value in embedding), metadata={"knowledge_base_id": str(knowledge_base_id), "document_version_id": str(document_version_id), "chunk_index": str(chunk.chunk_index), "content_hash": chunk.content_hash}) for chunk, embedding in zip(chunks, embeddings, strict=True)]

    async def _load_version(self, version_id: UUID, owner_id: UUID, is_admin: bool):
        stmt = (select(KnowledgeDocumentVersion, KnowledgeDocument, KnowledgeBase).join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id).join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id).where(KnowledgeDocumentVersion.id == version_id))
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        row = (await self.db.execute(stmt)).one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Document version 不存在或无权访问")
        return row

    async def index_version(self, version_id: UUID, owner_id: UUID, is_admin: bool = False) -> tuple[str, int]:
        version, document, knowledge_base = await self._load_version(version_id, owner_id, is_admin)
        if settings.vector_provider == "none":
            version.vector_index_status = "skipped"
            version.embedding_model = None
            await self.db.commit()
            return "skipped", 0
        if settings.vector_provider != "pgvector":
            raise HTTPException(status_code=503, detail=f"Unsupported VECTOR_PROVIDER: {settings.vector_provider}")
        supported_providers = {"openai-compatible", "ollama", "mock"}
        if settings.embedding_provider not in supported_providers:
            version.vector_index_status = "failed"
            await self.db.commit()
            raise HTTPException(status_code=503, detail="VECTOR_PROVIDER=pgvector requires EMBEDDING_PROVIDER=openai-compatible, ollama or mock")
        if settings.embedding_provider in {"openai-compatible", "ollama"} and not settings.embedding_model:
            version.vector_index_status = "failed"
            await self.db.commit()
            raise HTTPException(status_code=503, detail="EMBEDDING_MODEL is required for vector indexing")
        if settings.embedding_provider == "openai-compatible" and (not settings.embedding_base_url or not settings.embedding_api_key):
            version.vector_index_status = "failed"
            await self.db.commit()
            raise HTTPException(status_code=503, detail="EMBEDDING_BASE_URL and EMBEDDING_API_KEY are required for vector indexing")
        if settings.embedding_provider == "ollama" and not settings.embedding_base_url:
            version.vector_index_status = "failed"
            await self.db.commit()
            raise HTTPException(status_code=503, detail="EMBEDDING_BASE_URL is required for Ollama vector indexing")
        version.vector_index_status = "processing"
        version.embedding_model = settings.embedding_model or "mock-semantic-v1"
        await self.db.commit()
        try:
            chunks = list((await self.db.execute(select(KnowledgeDocumentChunk).where(KnowledgeDocumentChunk.document_version_id == version.id).order_by(KnowledgeDocumentChunk.chunk_index.asc()))).scalars().all())
            if settings.embedding_provider == "mock":
                embedding_provider = MockEmbeddingProvider(dimension=settings.embedding_dimension)
            elif settings.embedding_provider == "ollama":
                embedding_provider = OllamaEmbeddingProvider(base_url=settings.embedding_base_url, model=settings.embedding_model, timeout_seconds=settings.embedding_timeout_seconds, dimensions=(settings.embedding_dimension if settings.embedding_dimensions_parameter_enabled else None), expected_dimension=settings.embedding_dimension)
            else:
                embedding_provider = OpenAICompatibleEmbeddingProvider(base_url=settings.embedding_base_url, api_key=settings.embedding_api_key, model=settings.embedding_model, timeout_seconds=settings.embedding_timeout_seconds, dimensions=(settings.embedding_dimension if settings.embedding_dimensions_parameter_enabled else None), expected_dimension=settings.embedding_dimension)
            vector_provider = PgVectorRetrievalProvider(self.db, settings.embedding_dimension)
            batch_size = max(1, settings.embedding_batch_size)
            indexed = 0
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                embeddings = await embedding_provider.embed([chunk.content for chunk in batch])
                if any(len(embedding) != settings.embedding_dimension for embedding in embeddings):
                    raise EmbeddingProviderError(f"embedding dimensions do not match configured dimension {settings.embedding_dimension}")
                records = self.build_records(batch, embeddings, knowledge_base.id, version.id)
                await vector_provider.upsert(records)
                indexed += len(records)
            version.vector_index_status = "ready"
            await self.db.commit()
            return "ready", indexed
        except (EmbeddingProviderError, VectorRetrievalProviderError) as exc:
            await self.db.rollback()
            failed = await self._load_version(version_id, owner_id, is_admin)
            failed[0].vector_index_status = "failed"
            await self.db.commit()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception:
            await self.db.rollback()
            failed = await self._load_version(version_id, owner_id, is_admin)
            failed[0].vector_index_status = "failed"
            await self.db.commit()
            raise
