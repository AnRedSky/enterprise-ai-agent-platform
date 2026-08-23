from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization
from app.runtime.model_gateway import ModelGateway
from app.schemas.model_provider import ModelProviderRoutingRequest
from app.services.model_provider import ModelProviderService
from app.services.model_provider_governance_contract import FallbackReason


@dataclass(frozen=True)
class RuntimeProviderCandidate:
    profile: ModelProfile
    provider: ModelProvider


RuntimeInvocationAttemptCallback = Callable[
    [RuntimeProviderCandidate, str, str, FallbackReason | None, object | None],
    Awaitable[None],
]


class RuntimeModelGovernanceService:
    """Resolve governed model candidates and invoke them without mock success fallback."""

    def __init__(self, db: AsyncSession, gateway: ModelGateway | None = None):
        self.db = db
        self.gateway = gateway or ModelGateway()
        self.providers = ModelProviderService(db)

    async def resolve(self, request: ModelProviderRoutingRequest, user_id: UUID) -> list[RuntimeProviderCandidate]:
        selected = await self.providers.resolve_routing(request, user_id)
        if not selected:
            return []
        profile_ids = [item.profile_id for item in selected]
        rows = (
            await self.db.execute(
                select(ModelProfile, ModelProvider)
                .join(ModelProvider, ModelProvider.id == ModelProfile.provider_id)
                .join(Organization, Organization.id == ModelProvider.organization_id)
                .where(
                    ModelProfile.id.in_(profile_ids),
                    ModelProvider.organization_id == request.organization_id,
                    Organization.status == "active",
                )
            )
        ).all()
        by_profile = {profile.id: (profile, provider) for profile, provider in rows}
        return [
            RuntimeProviderCandidate(profile=by_profile[item.profile_id][0], provider=by_profile[item.profile_id][1])
            for item in selected
            if item.profile_id in by_profile
        ]

    @staticmethod
    def fallback_reason(exc: BaseException) -> FallbackReason | None:
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError)):
            return FallbackReason.CONNECTIVITY
        # Provider calls may time out while connecting, writing, reading, or waiting
        # for a pooled connection. ConnectTimeout is intentionally classified above
        # as connectivity; every other HTTPX timeout remains timeout-eligible.
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return FallbackReason.TIMEOUT
        if isinstance(exc, HTTPException):
            if exc.status_code == 429:
                return FallbackReason.RATE_LIMIT
            if 500 <= exc.status_code <= 599:
                return FallbackReason.PROVIDER_5XX
            return None
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status == 429:
                return FallbackReason.RATE_LIMIT
            if 500 <= status <= 599:
                return FallbackReason.PROVIDER_5XX
        return None

    async def invoke(
        self,
        request: ModelProviderRoutingRequest,
        user_id: UUID,
        messages: list[dict],
        *,
        max_attempts: int = 2,
        on_attempt: RuntimeInvocationAttemptCallback | None = None,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        candidates = await self.resolve(request, user_id)
        if not candidates:
            raise HTTPException(404, "没有符合治理策略的 Model Provider/Profile")

        attempts = 0
        last_error: BaseException | None = None
        for candidate in candidates:
            if attempts >= max_attempts:
                break
            attempts += 1
            request_id = str(uuid4())
            try:
                result = await self.gateway.generate(
                    candidate.profile.model_name,
                    messages,
                    model_profile=candidate.profile,
                    model_provider=candidate.provider,
                )
                if on_attempt is not None:
                    await on_attempt(candidate, request_id, "success", None, result)
                return result
            except Exception as exc:
                last_error = exc
                reason = self.fallback_reason(exc)
                if on_attempt is not None:
                    await on_attempt(candidate, request_id, "failed", reason, None)
                if reason is None:
                    raise

        if last_error is not None:
            raise last_error
        raise HTTPException(502, "Model Provider 调用失败")
