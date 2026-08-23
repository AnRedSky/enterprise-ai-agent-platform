"""Model Provider 路由规则实现。

模块职责：根据显式 Profile、组织默认策略、能力集合和 Provider 白名单筛选候选。
边界：只处理已经加载到内存中的领域候选，不访问数据库、不调用模型 Provider。
关键外部依赖：本领域 contract 中的 RoutingRequest、RoutingStrategy 与 ProviderCandidate。
"""

from .contract import ProviderCandidate, RoutingRequest, RoutingStrategy


def select_candidates(
    request: RoutingRequest,
    candidates: list[ProviderCandidate],
    strategy: RoutingStrategy,
) -> list[ProviderCandidate]:
    """Return deterministic, policy-filtered candidates; no provider-name fallback is allowed."""
    available = [item for item in candidates if item.enabled and item.model_type == request.model_type]
    if request.allowed_provider_ids:
        available = [item for item in available if item.provider_id in request.allowed_provider_ids]
    if request.required_capabilities:
        available = [item for item in available if request.required_capabilities <= item.capabilities]

    if request.profile_id is not None:
        selected = [item for item in available if item.profile_id == request.profile_id]
        if not selected:
            return []
        return selected

    if strategy is RoutingStrategy.EXPLICIT_PROFILE:
        return []

    defaults = [item for item in available if item.is_default]
    return sorted(defaults, key=lambda item: (item.provider_name, item.model_name, str(item.profile_id)))
