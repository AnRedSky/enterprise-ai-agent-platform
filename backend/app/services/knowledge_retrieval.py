from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion


class KnowledgeRetrievalService:
    """Provider-neutral deterministic retrieval contract for Phase 1.4.

    This first implementation intentionally uses lexical token overlap rather than
    binding the platform to a vector database or embedding provider.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[\w\u4e00-\u9fff]+", text.lower()) if token}

    @classmethod
    def _score(cls, query: str, content: str) -> float:
        query_tokens = cls._tokens(query)
        content_tokens = cls._tokens(content)
        if not query_tokens or not content_tokens:
            return 0.0
        return round(len(query_tokens & content_tokens) / len(query_tokens), 6)

    async def retrieve(
        self,
        query: str,
        top_k: int,
        owner_id: UUID,
        is_admin: bool = False,
        knowledge_base_id: UUID | None = None,
        document_id: UUID | None = None,
    ) -> list[dict]:
        if not query.strip():
            raise HTTPException(status_code=422, detail="query 不能为空")

        stmt = (
            select(KnowledgeDocumentChunk, KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeBase)
            .join(KnowledgeDocumentVersion, KnowledgeDocumentVersion.id == KnowledgeDocumentChunk.document_version_id)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
            .where(
                KnowledgeDocument.status == "active",
                KnowledgeDocumentVersion.ingestion_status == "ready",
                KnowledgeDocumentVersion.status == "ready",
            )
        )
        if knowledge_base_id:
            stmt = stmt.where(KnowledgeBase.id == knowledge_base_id)
        if document_id:
            stmt = stmt.where(KnowledgeDocument.id == document_id)
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)

        rows = (await self.db.execute(stmt)).all()
        scored = []
        for chunk, document, version, _knowledge_base in rows:
            score = self._score(query, chunk.content)
            if score <= 0:
                continue
            scored.append(
                {
                    "document_id": document.id,
                    "document_version_id": version.id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "source_document": document.title,
                    "source_uri": document.source_uri or version.source_uri,
                    "relevance_score": score,
                    "citation": f"{document.title}#{chunk.chunk_index}",
                    "content": chunk.content,
                }
            )

        scored.sort(key=lambda item: (-item["relevance_score"], str(item["document_id"]), item["chunk_index"]))
        return scored[:top_k]
