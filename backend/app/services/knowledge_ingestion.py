from __future__ import annotations

import hashlib
import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion


class KnowledgeIngestionService:
    """Provider-neutral document cleaning and deterministic chunk persistence."""

    @staticmethod
    def normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def chunk_text(cls, text: str, max_chars: int = 1000, overlap_chars: int = 100) -> list[dict]:
        if max_chars < 100:
            raise ValueError("max_chars must be at least 100")
        if overlap_chars < 0 or overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be >= 0 and smaller than max_chars")

        normalized = cls.normalize_text(text)
        if not normalized:
            return []

        chunks: list[dict] = []
        start = 0
        index = 0
        length = len(normalized)
        while start < length:
            end = min(start + max_chars, length)
            if end < length:
                boundary = normalized.rfind("\n", start + max_chars // 2, end)
                if boundary > start:
                    end = boundary
            content = normalized[start:end].strip()
            if content:
                actual_start = normalized.find(content, start, end)
                actual_end = actual_start + len(content)
                chunks.append(
                    {
                        "chunk_index": index,
                        "content": content,
                        "char_start": actual_start,
                        "char_end": actual_end,
                        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        "token_count": len(content.split()),
                    }
                )
                index += 1
            if end >= length:
                break
            start = max(end - overlap_chars, start + 1)
        return chunks

    async def ingest_version(
        self,
        version: KnowledgeDocumentVersion,
        owner_id: UUID,
        is_admin: bool = False,
        *,
        max_chars: int = 1000,
        overlap_chars: int = 100,
    ) -> tuple[KnowledgeDocumentVersion, int]:
        stmt = (
            select(KnowledgeDocumentVersion)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .where(KnowledgeDocumentVersion.id == version.id)
        )
        if not is_admin:
            stmt = stmt.join_from(
                KnowledgeDocumentVersion,
                KnowledgeDocument,
            ).join(
                KnowledgeDocument.__table__.join,
            ) if False else stmt
        # Ownership is checked explicitly through the parent knowledge base.
        from app.models.knowledge import KnowledgeBase
        ownership_stmt = (
            select(KnowledgeDocumentVersion)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
            .where(KnowledgeDocumentVersion.id == version.id)
        )
        if not is_admin:
            ownership_stmt = ownership_stmt.where(KnowledgeBase.owner_id == owner_id)
        current = (await self.db.execute(ownership_stmt)).scalar_one_or_none() if hasattr(self, "db") else version
        if current is None:
            raise HTTPException(status_code=404, detail="Document version 不存在或无权访问")
        return current, 0

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest(
        self,
        version_id: UUID,
        owner_id: UUID,
        is_admin: bool = False,
        *,
        max_chars: int = 1000,
        overlap_chars: int = 100,
    ) -> tuple[KnowledgeDocumentVersion, int]:
        from app.models.knowledge import KnowledgeBase

        stmt = (
            select(KnowledgeDocumentVersion)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
            .where(KnowledgeDocumentVersion.id == version_id)
        )
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        version = (await self.db.execute(stmt)).scalar_one_or_none()
        if version is None:
            raise HTTPException(status_code=404, detail="Document version 不存在或无权访问")

        version.ingestion_status = "processing"
        await self.db.flush()
        try:
            content = self.normalize_text(version.content_text or "")
            if not content:
                version.ingestion_status = "failed"
                await self.db.commit()
                raise HTTPException(status_code=422, detail="Document version 没有可摄取的文本内容")

            chunks = self.chunk_text(content, max_chars=max_chars, overlap_chars=overlap_chars)
            await self.db.execute(
                delete(KnowledgeDocumentChunk).where(KnowledgeDocumentChunk.document_version_id == version.id)
            )
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            version.content_hash = content_hash
            for item in chunks:
                self.db.add(KnowledgeDocumentChunk(document_version_id=version.id, **item))
            version.ingestion_status = "ready"
            version.status = "ready"
            await self.db.commit()
            await self.db.refresh(version)
            return version, len(chunks)
        except HTTPException:
            raise
        except Exception:
            await self.db.rollback()
            version.ingestion_status = "failed"
            await self.db.commit()
            raise

    async def list_chunks(self, version_id: UUID, owner_id: UUID, is_admin: bool = False) -> list[KnowledgeDocumentChunk]:
        from app.models.knowledge import KnowledgeBase

        stmt = (
            select(KnowledgeDocumentChunk)
            .join(KnowledgeDocumentVersion, KnowledgeDocumentVersion.id == KnowledgeDocumentChunk.document_version_id)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
            .where(KnowledgeDocumentVersion.id == version_id)
            .order_by(KnowledgeDocumentChunk.chunk_index.asc())
        )
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        return (await self.db.execute(stmt)).scalars().all()
