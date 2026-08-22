from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims
from app.dependencies.db import get_db
from app.schemas.organization import (
    MembershipCreate,
    MembershipListResponse,
    MembershipResponse,
    MembershipUpdate,
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization import OrganizationService

router = APIRouter()


def _user_id(claims: dict) -> UUID:
    return UUID(claims["sub"])


def _request_context(request_id: str | None, trace_id: str | None) -> tuple[str | None, str | None]:
    return request_id, trace_id


def _organization_response(item) -> OrganizationResponse:
    return OrganizationResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        name=item.name,
        status=item.status,
    )


def _membership_response(item) -> MembershipResponse:
    return MembershipResponse(
        id=item.id,
        organization_id=item.organization_id,
        user_id=item.user_id,
        status=item.status,
        role=item.role,
    )


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    items, total = await OrganizationService(db).list_for_user(_user_id(claims), offset, limit)
    return OrganizationListResponse(items=[_organization_response(item) for item in items], total=total)


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    payload: OrganizationCreate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    request_id, trace_id = _request_context(x_request_id, x_trace_id)
    item = await OrganizationService(db).create(
        payload.name,
        _user_id(claims),
        request_id=request_id,
        trace_id=trace_id,
    )
    return _organization_response(item)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    service = OrganizationService(db)
    await service.require_active_membership(organization_id, _user_id(claims))
    return _organization_response(await service.get(organization_id))


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    request_id, trace_id = _request_context(x_request_id, x_trace_id)
    item = await OrganizationService(db).update(
        organization_id,
        _user_id(claims),
        name=payload.name,
        status=payload.status,
        request_id=request_id,
        trace_id=trace_id,
    )
    return _organization_response(item)


@router.get("/{organization_id}/members", response_model=MembershipListResponse)
async def list_members(
    organization_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    items, total = await OrganizationService(db).list_members(
        organization_id, _user_id(claims), offset, limit
    )
    return MembershipListResponse(items=[_membership_response(item) for item in items], total=total)


@router.post("/{organization_id}/members", response_model=MembershipResponse, status_code=201)
async def add_member(
    organization_id: UUID,
    payload: MembershipCreate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    request_id, trace_id = _request_context(x_request_id, x_trace_id)
    item = await OrganizationService(db).add_member(
        organization_id,
        _user_id(claims),
        payload.user_id,
        payload.role,
        request_id=request_id,
        trace_id=trace_id,
    )
    return _membership_response(item)


@router.patch("/{organization_id}/members/{membership_id}", response_model=MembershipResponse)
async def update_member(
    organization_id: UUID,
    membership_id: UUID,
    payload: MembershipUpdate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    request_id, trace_id = _request_context(x_request_id, x_trace_id)
    item = await OrganizationService(db).update_member(
        organization_id,
        membership_id,
        _user_id(claims),
        role=payload.role,
        status=payload.status,
        request_id=request_id,
        trace_id=trace_id,
    )
    return _membership_response(item)


@router.post("/{organization_id}/members/{membership_id}/transfer-owner", response_model=MembershipResponse)
async def transfer_owner(
    organization_id: UUID,
    membership_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    request_id, trace_id = _request_context(x_request_id, x_trace_id)
    item = await OrganizationService(db).transfer_owner(
        organization_id,
        _user_id(claims),
        membership_id,
        request_id=request_id,
        trace_id=trace_id,
    )
    return _membership_response(item)


@router.delete("/{organization_id}/members/{membership_id}", status_code=204)
async def remove_member(
    organization_id: UUID,
    membership_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    request_id, trace_id = _request_context(x_request_id, x_trace_id)
    await OrganizationService(db).remove_member(
        organization_id,
        membership_id,
        _user_id(claims),
        request_id=request_id,
        trace_id=trace_id,
    )
    return Response(status_code=204)
