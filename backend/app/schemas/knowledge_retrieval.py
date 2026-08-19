from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeRetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    dedupe: bool = True
    knowledge_base_id: UUID | None = None
    document_id: UUID | None = None


class KnowledgeRetrievalSource(BaseModel):
    document_id: UUID
    document_version_id: UUID
    chunk_id: UUID
    chunk_index: int
    source_document: str
    source_uri: str | None = None
    relevance_score: float = Field(ge=0, le=1)
    citation: str
    content: str
    matched_terms: list[str] = Field(default_factory=list)
    retrieval_mode: str = "lexical-v2"


class KnowledgeRetrievalResponse(BaseModel):
    query: str
    top_k: int
    min_score: float
    retrieval_mode: str
    results: list[KnowledgeRetrievalSource]
