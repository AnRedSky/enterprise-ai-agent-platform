from __future__ import annotations

import hashlib
import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion


class KnowledgeIngestionService:
    """Provider-neutral document cleaning and deterministic chunk persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

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
        while start < len(normalized):
            end = min(start + max_chars, len(normalized))
            if end < len(normalized):
                boundary = normalized.rfind("\n", start + max_chars // 2, end)
                if boundary > start:
                    end = boundary
            content = normalized[start:end].strip()
            if content:
                actual_start = normalized.find(content, start, end)
                actual_end = actual_start + len(content)
                chunks.append({
                    "chunk_index": index,
                    "content": content,
                    "char_start": actual_start,
                    "char_end": actual_end,
                    "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "token_count": len(content.split()),
                })
                index += 1
            if end >= len(normalized):
                break
            start = max(end - overlap_chars, start + 1)
        return chunks

    async def _get_version(self, version_id: UUID, owner_id: UUID, is_admin: bool) -> KnowledgeDocumentVersion:
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
        return version

    async def ingest(
        self,
        version_id: UUID,
        owner_id: UUID,
        is_admin: bool = False,
        *,
        max_chars: int = 1000,
        overlap_chars: int = 100,
    ) -> tuple[KnowledgeDocumentVersion, int]:
        version = await self._get_version(version_id, owner_id, is_admin)
        version.ingestion_status = "processing"
        await self.db.flush()
        try:
            content = self.normalize_text(version.content_text or "")
            if not content:
                version.ingestion_status = "failed"
                await self.db.commit()
                raise HTTPException(status_code=422, detail="Document version 没有可摄取的文本内容")

            chunks = self.chunk_text(content, max_chars=max_chars, overlap_chars=overlap_chars)
            await self.db.execute(delete(KnowledgeDocumentChunk).where(KnowledgeDocumentChunk.document_version_id == version.id))
            version.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            for item in chunks:
                self.db.add(KnowledgeDocumentChunk(document_version_id=version.id, **item))

            document = await self.db.get(KnowledgeDocument, version.document_id)
            if document is None:
                raise HTTPException(status_code=404, detail="Document 不存在")
            document.current_version_id = version.id
            version.ingestion_status = "ready"
            version.status = "ready"
            await self.db.commit()
            await self.db.refresh(version)
            return version, len(chunks)
        except HTTPException:
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def list_chunks(self, version_id: UUID, owner_id: UUID, is_admin: bool = False) -> list[KnowledgeDocumentChunk]:
        await self._get_version(version_id, owner_id, is_admin)
        stmt = select(KnowledgeDocumentChunk).where(
            KnowledgeDocumentChunk.document_version_id == version_id
        ).order_by(KnowledgeDocumentChunk.chunk_index.asc())
        return (await self.db.execute(stmt)).scalars().all()
