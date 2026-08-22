from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, pattern="^(active|suspended)$")


class MembershipCreate(BaseModel):
    user_id: UUID
    role: str = Field(default="member", pattern="^(admin|member)$")


class MembershipUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|member)$")
    status: str | None = Field(default=None, pattern="^(active|suspended|removed)$")


class OrganizationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    status: str


class MembershipResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    status: str
    role: str


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]
    total: int


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int
