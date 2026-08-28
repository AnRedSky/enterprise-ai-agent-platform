"""Agent Delegation 领域身份与预算校验。

职责：集中计算 Delegation 稳定身份并校验首版治理预算，避免 API、Worker 或测试复制规则。
边界：不访问数据库，不负责状态迁移或权限查询。
关键依赖：UUID 类型与调用方提供的治理配置。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException


def delegation_identity_key(*, tenant_id: UUID, source_execution_id: UUID, delegation_key: str) -> str:
    """生成稳定 Delegation 业务身份。

    Args:
        tenant_id: 租户身份。
        source_execution_id: 委派来源 Execution。
        delegation_key: 来源 Execution 内部声明的业务幂等键。

    Returns:
        用于日志、诊断和数据库查询的稳定身份字符串。

    Raises:
        HTTPException: delegation_key 为空或超出 128 字符。
    """
    key = delegation_key.strip()
    if not key or len(key) > 128:
        raise HTTPException(422, "delegation_key 必须为 1-128 字符")
    return f"{tenant_id}:{source_execution_id}:{key}"


def validate_budget(*, max_delegation_depth: int, max_active_delegations: int, timeout_seconds: int, model_budget: dict) -> tuple[int, int, int, dict]:
    """校验 Delegation 的深度、并发、超时和模型预算边界。"""
    for name, value, minimum, maximum in (
        ("max_delegation_depth", max_delegation_depth, 1, 20),
        ("max_active_delegations", max_active_delegations, 1, 100),
        ("timeout_seconds", timeout_seconds, 1, 86_400),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise HTTPException(422, f"{name} 必须在 {minimum}-{maximum} 范围内")
    if not isinstance(model_budget, dict):
        raise HTTPException(422, "model_budget 必须为对象")
    for key, value in model_budget.items():
        if not isinstance(key, str) or not key or len(key) > 64:
            raise HTTPException(422, "model_budget 字段名无效")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise HTTPException(422, "model_budget 数值必须为非负数字")
    return max_delegation_depth, max_active_delegations, timeout_seconds, dict(model_budget)
