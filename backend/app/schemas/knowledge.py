from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    status: str = Field(default="active", pattern="^(active|disabled|archived)$")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(active|disabled|archived)$")


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    owner_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_type: str = Field(default="manual", min_length=1, max_length=32)
    source_uri: str | None = Field(default=None, max_length=1000)


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: str | None = Field(default=None, min_length=1, max_length=32)
    source_uri: str | None = Field(default=None, max_length=1000)
    status: str | None = Field(default=None, pattern="^(active|disabled|archived)$")


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_base_id: UUID
    title: str
    source_type: str
    source_uri: str | None
    status: str
    current_version_id: UUID | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentVersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=32)
    source_uri: str | None = Field(default=None, max_length=1000)
    content_hash: str | None = Field(default=None, max_length=128)
    content_text: str | None = None
    status: str = Field(default="draft", pattern="^(draft|ready|failed)$")


class KnowledgeDocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version: str
    status: str
    source_uri: str | None
    content_hash: str | None
    content_text: str | None
    created_by: UUID
    created_at: datetime


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
