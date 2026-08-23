"""Model 领域治理 Contract 定义。

模块职责：定义 Provider 路由、Fallback、成本计量与使用追踪所需的领域值对象。
边界：只表达稳定领域契约，不执行数据库查询、不调用外部 Provider。
关键外部依赖：Python dataclasses、Enum 与 UUID 标准库类型。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping
from uuid import UUID


class RoutingStrategy(StrEnum):
    EXPLICIT_PROFILE = "explicit_profile"
    ORGANIZATION_DEFAULT = "organization_default"


class FallbackReason(StrEnum):
    CONNECTIVITY = "connectivity"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    PROVIDER_5XX = "provider_5xx"


class CostUnit(StrEnum):
    INPUT_TOKEN = "input_token"
    OUTPUT_TOKEN = "output_token"
    EMBEDDING_TOKEN = "embedding_token"
    REQUEST = "request"


class PricingSource(StrEnum):
    PROVIDER_PRICING = "provider_pricing"
    PLATFORM_PRICING = "platform_pricing"


@dataclass(frozen=True)
class ProviderCandidate:
    provider_id: UUID
    profile_id: UUID
    model_type: str
    model_name: str
    enabled: bool
    is_default: bool
    capabilities: frozenset[str]
    provider_name: str


@dataclass(frozen=True)
class RoutingRequest:
    organization_id: UUID
    model_type: str
    profile_id: UUID | None = None
    required_capabilities: frozenset[str] = frozenset()
    allowed_provider_ids: frozenset[UUID] = frozenset()


@dataclass(frozen=True)
class FallbackPolicy:
    enabled: bool = True
    max_attempts: int = 2
    eligible_reasons: frozenset[FallbackReason] = frozenset(FallbackReason)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.max_attempts > 2:
            raise ValueError("max_attempts must be <= 2")


@dataclass(frozen=True)
class CostPolicy:
    units: tuple[CostUnit, ...]
    pricing_source: PricingSource
    pricing_version: str

    def __post_init__(self) -> None:
        if not self.units:
            raise ValueError("at least one cost unit is required")
        if not self.pricing_version.strip():
            raise ValueError("pricing_version is required")


@dataclass(frozen=True)
class UsageIdentity:
    organization_id: UUID
    provider_id: UUID
    profile_id: UUID
    model_type: str
    request_id: str
    trace_id: str
    outcome: str


@dataclass(frozen=True)
class ProviderGovernanceContract:
    routing_strategy: RoutingStrategy = RoutingStrategy.EXPLICIT_PROFILE
    fallback: FallbackPolicy = FallbackPolicy()
    cost: CostPolicy = CostPolicy(
        units=(CostUnit.INPUT_TOKEN, CostUnit.OUTPUT_TOKEN),
        pricing_source=PricingSource.PROVIDER_PRICING,
        pricing_version="unconfigured",
    )


def usage_dimensions(identity: UsageIdentity) -> Mapping[str, str]:
    """生成不包含 credential/API key 的可审计使用维度。"""
    return {
        "organization_id": str(identity.organization_id),
        "provider_id": str(identity.provider_id),
        "profile_id": str(identity.profile_id),
        "model_type": identity.model_type,
        "request_id": identity.request_id,
        "trace_id": identity.trace_id,
        "outcome": identity.outcome,
    }
