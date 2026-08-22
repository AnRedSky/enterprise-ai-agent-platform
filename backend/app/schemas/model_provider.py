from uuid import UUID

from pydantic import BaseModel, Field


class ModelProviderCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=100)
    provider_type: str = Field(min_length=1, max_length=50)
    provider_name: str = Field(min_length=1, max_length=100)
    endpoint: str | None = Field(default=None, max_length=500)
    credential_ref: str | None = Field(default=None, max_length=200)
    enabled: bool = True
    metadata: dict = Field(default_factory=dict)


class ModelProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    endpoint: str | None = Field(default=None, max_length=500)
    credential_ref: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    metadata: dict | None = None


class ModelProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model_type: str = Field(pattern="^(chat|embedding)$")
    model_name: str = Field(min_length=1, max_length=200)
    dimension: int | None = Field(default=None, ge=1)
    capabilities: dict = Field(default_factory=dict)
    parameters: dict = Field(default_factory=dict)
    enabled: bool = True
    is_default: bool = False


class ModelProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    dimension: int | None = Field(default=None, ge=1)
    capabilities: dict | None = None
    parameters: dict | None = None
    enabled: bool | None = None
    is_default: bool | None = None


class ModelProviderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    provider_type: str
    provider_name: str
    endpoint: str | None
    credential_ref: str | None
    enabled: bool
    metadata: dict


class ModelProfileResponse(BaseModel):
    id: UUID
    provider_id: UUID
    name: str
    model_type: str
    model_name: str
    dimension: int | None
    capabilities: dict
    parameters: dict
    enabled: bool
    is_default: bool


class ModelProviderListResponse(BaseModel):
    items: list[ModelProviderResponse]
    total: int
