from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims
from app.dependencies.db import get_db
from app.schemas.usage import ModelUsageListResponse, ModelUsageRecordResponse
from app.services.usage_accounting import UsageAccountingService

router = APIRouter()


def _user_id(claims: dict) -> UUID:
    return UUID(claims["sub"])


def _item(item: object) -> ModelUsageRecordResponse:
    return ModelUsageRecordResponse(
        id=item.id,
        organization_id=item.organization_id,
        tenant_id=item.tenant_id,
        execution_id=item.execution_id,
        workflow_id=item.workflow_id,
        node_id=item.node_id,
        provider_id=item.provider_id,
        profile_id=item.profile_id,
        model_type=item.model_type,
        model_name=item.model_name,
        request_id=item.request_id,
        trace_id=item.trace_id,
        outcome=item.outcome,
        fallback_reason=item.fallback_reason,
        prompt_tokens=item.prompt_tokens,
        completion_tokens=item.completion_tokens,
        total_tokens=item.total_tokens,
        request_units=item.request_units,
        cost_units=item.cost_units or [],
        pricing_source=item.pricing_source,
        pricing_version=item.pricing_version,
        input_cost=item.input_cost,
        output_cost=item.output_cost,
        request_cost=item.request_cost,
        total_cost=item.total_cost,
        created_at=item.created_at,
    )


@router.get("/model", response_model=ModelUsageListResponse)
async def list_model_usage(
    organization_id: UUID,
    execution_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    items, total, total_cost = await UsageAccountingService(db).list_for_organization(
        organization_id,
        _user_id(claims),
        execution_id=execution_id,
        offset=offset,
        limit=limit,
    )
    return ModelUsageListResponse(items=[_item(item) for item in items], total=total, total_cost=total_cost)
