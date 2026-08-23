from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge.hybrid import HybridCandidate, HybridRetrievalConfig, HybridRetrievalService
from app.services.knowledge.retrieval import KnowledgeRetrievalService
from app.services.knowledge.vector_retrieval import VectorKnowledgeRetrievalService


class HybridKnowledgeRetrievalService:
    RETRIEVAL_MODE = "hybrid"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(self, query: str, top_k: int, owner_id: UUID, is_admin: bool = False, knowledge_base_id: UUID | None = None, document_id: UUID | None = None, min_score: float = 0.0, dedupe: bool = True, lexical_weight: float = 0.5, vector_weight: float = 0.5) -> list[dict]:
        if not query.strip():
            raise HTTPException(status_code=422, detail="query 不能为空")
        if not 0 <= min_score <= 1:
            raise HTTPException(status_code=422, detail="min_score 必须在 0 到 1 之间")
        lexical_results = await KnowledgeRetrievalService(self.db).retrieve(query=query, top_k=top_k, owner_id=owner_id, is_admin=is_admin, knowledge_base_id=knowledge_base_id, document_id=document_id, min_score=0.0, dedupe=dedupe)
        vector_results = await VectorKnowledgeRetrievalService(self.db).retrieve(query=query, top_k=top_k, owner_id=owner_id, is_admin=is_admin, knowledge_base_id=knowledge_base_id, document_id=document_id, min_score=0.0, dedupe=dedupe)
        lexical_candidates = [HybridCandidate(chunk_id=str(item["chunk_id"]), score=float(item["relevance_score"]), source="lexical", payload=item) for item in lexical_results]
        vector_candidates = [HybridCandidate(chunk_id=str(item["chunk_id"]), score=float(item["relevance_score"]), source="vector", payload=item) for item in vector_results]
        fused = HybridRetrievalService(HybridRetrievalConfig(lexical_weight=lexical_weight, vector_weight=vector_weight)).fuse(lexical_candidates, vector_candidates, top_k=top_k)
        results = []
        for candidate in fused:
            if candidate.score < min_score:
                continue
            payload = dict(candidate.payload)
            payload["relevance_score"] = candidate.score
            payload["retrieval_mode"] = self.RETRIEVAL_MODE
            payload["retrieval_sources"] = candidate.source.split("+")
            results.append(payload)
        return results[:top_k]
