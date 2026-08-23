from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims
from app.dependencies.db import get_db
from app.schemas.model_provider import (
    ModelProfileCreate,
    ModelProfileResponse,
    ModelProfileUpdate,
    ModelProviderCreate,
    ModelProviderListResponse,
    ModelProviderResponse,
    ModelProviderRoutingCandidate,
    ModelProviderRoutingRequest,
    ModelProviderRoutingResponse,
    ModelProviderUpdate,
)
from app.services.model_provider import ModelProviderService

router = APIRouter()


def _user_id(claims: dict) -> UUID:
    return UUID(claims["sub"])


def _provider(item) -> ModelProviderResponse:
    return ModelProviderResponse(
        id=item.id, organization_id=item.organization_id, name=item.name,
        provider_type=item.provider_type, provider_name=item.provider_name,
        endpoint=item.endpoint, credential_ref=item.credential_ref,
        enabled=item.enabled, metadata=item.metadata_json or {},
    )


def _profile(item) -> ModelProfileResponse:
    return ModelProfileResponse(
        id=item.id, provider_id=item.provider_id, name=item.name,
        model_type=item.model_type, model_name=item.model_name,
        dimension=item.dimension, capabilities=item.capabilities or {},
        parameters=item.parameters or {}, enabled=item.enabled, is_default=item.is_default,
    )


@router.get("", response_model=ModelProviderListResponse)
async def list_model_providers(
    organization_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    items, total = await ModelProviderService(db).list_providers(organization_id, _user_id(claims), offset, limit)
    return ModelProviderListResponse(items=[_provider(item) for item in items], total=total)


@router.post("", response_model=ModelProviderResponse, status_code=201)
async def create_model_provider(
    payload: ModelProviderCreate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    item = await ModelProviderService(db).create_provider(payload, _user_id(claims), x_request_id, x_trace_id)
    return _provider(item)


@router.post("/routing/resolve", response_model=ModelProviderRoutingResponse)
async def resolve_model_provider_routing(
    payload: ModelProviderRoutingRequest,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    candidates = await ModelProviderService(db).resolve_routing(payload, _user_id(claims))
    return ModelProviderRoutingResponse(
        routing_strategy=payload.routing_strategy,
        candidates=[
            ModelProviderRoutingCandidate(
                provider_id=item.provider_id,
                profile_id=item.profile_id,
                model_type=item.model_type,
                model_name=item.model_name,
                provider_name=item.provider_name,
                is_default=item.is_default,
                capabilities=sorted(item.capabilities),
            )
            for item in candidates
        ],
    )


@router.get("/{provider_id}/profiles", response_model=list[ModelProfileResponse])
async def list_model_profiles(
    provider_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    _, items = await ModelProviderService(db).list_profiles(provider_id, _user_id(claims))
    return [_profile(item) for item in items]


@router.post("/{provider_id}/profiles", response_model=ModelProfileResponse, status_code=201)
async def create_model_profile(
    provider_id: UUID,
    payload: ModelProfileCreate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    item = await ModelProviderService(db).create_profile(provider_id, payload, _user_id(claims), x_request_id, x_trace_id)
    return _profile(item)


@router.patch("/{provider_id}", response_model=ModelProviderResponse)
async def update_model_provider(
    provider_id: UUID,
    payload: ModelProviderUpdate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    item = await ModelProviderService(db).update_provider(provider_id, payload, _user_id(claims), x_request_id, x_trace_id)
    return _provider(item)


@router.delete("/{provider_id}", status_code=204)
async def delete_model_provider(
    provider_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    await ModelProviderService(db).delete_provider(provider_id, _user_id(claims), x_request_id, x_trace_id)
    return Response(status_code=204)


@router.patch("/model-profiles/{profile_id}", response_model=ModelProfileResponse)
async def update_model_profile(
    profile_id: UUID,
    payload: ModelProfileUpdate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    item = await ModelProviderService(db).update_profile(profile_id, payload, _user_id(claims), x_request_id, x_trace_id)
    return _profile(item)


@router.delete("/model-profiles/{profile_id}", status_code=204)
async def delete_model_profile(
    profile_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
    x_request_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
):
    await ModelProviderService(db).delete_profile(profile_id, _user_id(claims), x_request_id, x_trace_id)
    return Response(status_code=204)
