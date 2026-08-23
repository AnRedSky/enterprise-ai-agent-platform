from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion


class KnowledgeRetrievalService:
    """Provider-neutral lexical retrieval with deterministic quality and safety controls."""

    RETRIEVAL_MODE = "lexical-v2"
    DEFAULT_MIN_SCORE = 0.0
    MAX_CANDIDATES = 5000

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _tokens(text: str) -> set[str]:
        tokens: set[str] = set()
        for match in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
            if not match:
                continue
            tokens.add(match)
            if re.fullmatch(r"[\u4e00-\u9fff]+", match):
                tokens.update(match[index : index + 2] for index in range(len(match) - 1))
        return tokens

    @classmethod
    def _score_details(cls, query: str, content: str) -> tuple[float, list[str]]:
        query_tokens = cls._tokens(query)
        content_tokens = cls._tokens(content)
        if not query_tokens or not content_tokens:
            return 0.0, []
        matched = sorted(query_tokens & content_tokens)
        token_recall = len(matched) / len(query_tokens)
        normalized_query = " ".join(query.lower().split())
        normalized_content = " ".join(content.lower().split())
        phrase_bonus = 0.15 if normalized_query and normalized_query in normalized_content else 0.0
        return min(1.0, round(token_recall * 0.85 + phrase_bonus, 6)), matched

    @classmethod
    def _score(cls, query: str, content: str) -> float:
        return cls._score_details(query, content)[0]

    async def retrieve(self, query: str, top_k: int, owner_id: UUID, is_admin: bool = False, knowledge_base_id: UUID | None = None, document_id: UUID | None = None, min_score: float = DEFAULT_MIN_SCORE, dedupe: bool = True) -> list[dict]:
        if not query.strip():
            raise HTTPException(status_code=422, detail="query 不能为空")
        if not 0 <= min_score <= 1:
            raise HTTPException(status_code=422, detail="min_score 必须在 0 到 1 之间")
        stmt = (select(KnowledgeDocumentChunk, KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeBase).join(KnowledgeDocumentVersion, KnowledgeDocumentVersion.id == KnowledgeDocumentChunk.document_version_id).join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id).join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id).where(KnowledgeDocument.status == "active", KnowledgeDocumentVersion.ingestion_status == "ready", KnowledgeDocumentVersion.status == "ready"))
        if knowledge_base_id:
            stmt = stmt.where(KnowledgeBase.id == knowledge_base_id)
        if document_id:
            stmt = stmt.where(KnowledgeDocument.id == document_id)
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        rows = (await self.db.execute(stmt)).all()
        scored: list[dict] = []
        seen_content: set[str] = set()
        for chunk, document, version, _knowledge_base in rows[: self.MAX_CANDIDATES]:
            score, matched_terms = self._score_details(query, chunk.content)
            if score < min_score or score <= 0:
                continue
            content_key = chunk.content_hash or chunk.content
            if dedupe and content_key in seen_content:
                continue
            seen_content.add(content_key)
            scored.append({"document_id": document.id, "document_version_id": version.id, "chunk_id": chunk.id, "chunk_index": chunk.chunk_index, "source_document": document.title, "source_uri": document.source_uri or version.source_uri, "relevance_score": score, "citation": f"{document.title}#{chunk.chunk_index}", "content": chunk.content, "matched_terms": matched_terms, "retrieval_mode": self.RETRIEVAL_MODE})
        scored.sort(key=lambda item: (-item["relevance_score"], str(item["document_id"]), item["chunk_index"], str(item["chunk_id"])))
        return scored[:top_k]
