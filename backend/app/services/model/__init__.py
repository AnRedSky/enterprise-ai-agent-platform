"""Model 领域服务入口。

模块职责：提供模型 Provider/Profile 治理、路由与运行时治理的稳定领域入口。
边界：不实现具体外部模型 Provider，也不承担 Runtime 执行编排或 HTTP 协议适配。
关键外部依赖：SQLAlchemy AsyncSession、模型 ORM、OrganizationService，以及 infrastructure provider contract。
"""

from .contract import (
    CostPolicy,
    CostUnit,
    FallbackPolicy,
    FallbackReason,
    PricingSource,
    ProviderCandidate,
    ProviderGovernanceContract,
    RoutingRequest,
    RoutingStrategy,
    UsageIdentity,
    usage_dimensions,
)
from .governance import RuntimeInvocationAttemptCallback, RuntimeModelGovernanceService, RuntimeProviderCandidate
from .provider import ModelProviderService
from .routing import select_candidates

__all__ = [
    "CostPolicy",
    "CostUnit",
    "FallbackPolicy",
    "FallbackReason",
    "ModelProviderService",
    "PricingSource",
    "ProviderCandidate",
    "ProviderGovernanceContract",
    "RoutingRequest",
    "RoutingStrategy",
    "RuntimeInvocationAttemptCallback",
    "RuntimeModelGovernanceService",
    "RuntimeProviderCandidate",
    "UsageIdentity",
    "select_candidates",
    "usage_dimensions",
]
