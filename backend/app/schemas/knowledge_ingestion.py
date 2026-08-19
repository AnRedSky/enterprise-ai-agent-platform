from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeIngestRequest(BaseModel):
    max_chars: int = Field(default=1000, ge=100, le=10000)
    overlap_chars: int = Field(default=100, ge=0, le=2000)


class KnowledgeIngestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: UUID
    ingestion_status: str
    vector_index_status: str
    embedding_model: str | None
    chunk_count: int
    content_hash: str


class KnowledgeChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_version_id: UUID
    chunk_index: int
    content: str
    char_start: int
    char_end: int
    content_hash: str
    token_count: int
    created_at: datetime
