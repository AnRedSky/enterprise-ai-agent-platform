from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_provider import ModelProfile
from app.models.usage import ModelUsageRecord
from app.services.model_provider_governance_contract import CostUnit, PricingSource
from app.services.organization import OrganizationService


class UsageAccountingService:
    """持久化受治理 Provider 的调用用量，并按已配置价格执行确定性成本计算。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.organizations = OrganizationService(db)

    @staticmethod
    def _decimal(value: Any, default: str = "0") -> Decimal:
        if value is None:
            return Decimal(default)
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise HTTPException(422, "pricing values must be numeric") from exc
        if result < 0:
            raise HTTPException(422, "pricing values must be non-negative")
        return result

    @classmethod
    def pricing_from_profile(cls, profile: ModelProfile) -> tuple[str, str, Decimal, Decimal, Decimal]:
        pricing = (profile.parameters or {}).get("pricing") or {}
        if not isinstance(pricing, dict):
            raise HTTPException(422, "model profile pricing must be an object")
        source = str(pricing.get("pricing_source", PricingSource.PROVIDER_PRICING.value))
        allowed_sources = {item.value for item in PricingSource}
        if source not in allowed_sources:
            raise HTTPException(422, "unsupported pricing_source")
        version = str(pricing.get("pricing_version", "unconfigured")).strip()
        if not version:
            raise HTTPException(422, "pricing_version is required")
        return (
            source,
            version,
            cls._decimal(pricing.get("input_token_per_1k")),
            cls._decimal(pricing.get("output_token_per_1k")),
            cls._decimal(pricing.get("request")),
        )

    @staticmethod
    def calculate_cost(
        prompt_tokens: int | None,
        completion_tokens: int | None,
        request_units: int,
        input_rate_per_1k: Decimal,
        output_rate_per_1k: Decimal,
        request_rate: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, list[str]]:
        prompt = max(prompt_tokens or 0, 0)
        completion = max(completion_tokens or 0, 0)
        requests = max(request_units, 0)
        input_cost = Decimal(prompt) / Decimal("1000") * input_rate_per_1k
        output_cost = Decimal(completion) / Decimal("1000") * output_rate_per_1k
        request_cost = Decimal(requests) * request_rate
        units: list[str] = [CostUnit.REQUEST.value] if requests else []
        if prompt_tokens is not None:
            units.append(CostUnit.INPUT_TOKEN.value)
        if completion_tokens is not None:
            units.append(CostUnit.OUTPUT_TOKEN.value)
        total = input_cost + output_cost + request_cost
        return input_cost, output_cost, request_cost, total, units

    async def record_attempt(
        self,
        *,
        organization_id: UUID,
        tenant_id: UUID,
        execution_id: UUID | None,
        workflow_id: UUID | None,
        node_id: str | None,
        provider_id: UUID,
        profile: ModelProfile,
        request_id: str,
        trace_id: str,
        outcome: str,
        fallback_reason: str | None,
        usage: dict[str, Any] | None,
    ) -> ModelUsageRecord:
        source, version, input_rate, output_rate, request_rate = self.pricing_from_profile(profile)
        usage = usage or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        input_cost, output_cost, request_cost, total_cost, units = self.calculate_cost(
            prompt_tokens, completion_tokens, 1, input_rate, output_rate, request_rate
        )
        record = ModelUsageRecord(
            organization_id=organization_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            workflow_id=workflow_id,
            node_id=node_id,
            provider_id=provider_id,
            profile_id=profile.id,
            model_type=profile.model_type,
            model_name=profile.model_name,
            request_id=request_id,
            trace_id=trace_id,
            outcome=outcome,
            fallback_reason=fallback_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            request_units=1,
            cost_units=units,
            pricing_source=source,
            pricing_version=version,
            input_token_rate_per_1k=input_rate,
            output_token_rate_per_1k=output_rate,
            request_rate=request_rate,
            input_cost=input_cost,
            output_cost=output_cost,
            request_cost=request_cost,
            total_cost=total_cost,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_for_organization(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        execution_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ModelUsageRecord], int, Decimal]:
        await self.organizations.require_active_membership(organization_id, user_id)
        base = select(ModelUsageRecord).where(ModelUsageRecord.organization_id == organization_id)
        count_query = select(func.count(ModelUsageRecord.id)).where(ModelUsageRecord.organization_id == organization_id)
        sum_query = select(func.coalesce(func.sum(ModelUsageRecord.total_cost), 0)).where(ModelUsageRecord.organization_id == organization_id)
        if execution_id is not None:
            base = base.where(ModelUsageRecord.execution_id == execution_id)
            count_query = count_query.where(ModelUsageRecord.execution_id == execution_id)
            sum_query = sum_query.where(ModelUsageRecord.execution_id == execution_id)
        items = list((await self.db.execute(base.order_by(ModelUsageRecord.created_at.asc(), ModelUsageRecord.id.asc()).offset(offset).limit(limit))).scalars().all())
        total = int((await self.db.execute(count_query)).scalar_one())
        total_cost = Decimal(str((await self.db.execute(sum_query)).scalar_one()))
        return items, total, total_cost
