"""Agent Delegation 生命周期与 Worker fencing 规则。

职责：集中定义 Delegation 的状态转换、Worker completion fencing 与超时判定。
边界：不执行数据库写入、不创建 Workflow Execution；事务与持久化由 AgentDelegationService 负责。
关键依赖：Delegation 状态值、Worker execution identity。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID


TERMINAL_STATES = frozenset({"completed", "failed", "timed_out", "cancelled"})
TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"running", "cancelled"}),
    "running": frozenset({"completed", "failed", "timed_out", "cancelled"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "timed_out": frozenset(),
    "cancelled": frozenset(),
}


def validate_transition(current_status: str, target_status: str) -> None:
    """校验 Delegation 状态转换是否符合冻结 Contract。

    Args:
        current_status: 当前持久化状态。
        target_status: 请求进入的目标状态。

    Returns:
        None。校验通过时不返回业务值。

    Raises:
        ValueError: 状态未知或转换不被允许。
    """
    if current_status not in TRANSITIONS or target_status not in TRANSITIONS:
        raise ValueError("Delegation 状态不存在")
    if target_status not in TRANSITIONS[current_status]:
        raise ValueError(f"Delegation 不允许从 {current_status} 转换到 {target_status}")


def validate_worker_fence(
    *,
    status: str,
    worker_execution_id: UUID | None,
    expected_worker_execution_id: UUID,
) -> None:
    """校验 Worker completion 是否仍属于当前 Delegation generation。

    Args:
        status: 当前 Delegation 状态。
        worker_execution_id: 持久化的当前 Worker execution identity。
        expected_worker_execution_id: 完成请求携带的 Worker execution identity。

    Returns:
        None。通过后允许 Service 在同一事务中继续写入完成事实。

    Raises:
        ValueError: Delegation 已非 running、缺少 owner identity 或 identity 不匹配。
    """
    if status != "running":
        raise ValueError("只有 running Delegation 才允许 Worker completion")
    if worker_execution_id is None:
        raise ValueError("running Delegation 缺少 Worker execution identity")
    if worker_execution_id != expected_worker_execution_id:
        raise ValueError("Worker completion fencing 校验失败")


def is_timeout_due(timeout_at: datetime | None, *, now: datetime) -> bool:
    """判断 Delegation 是否已经到达超时边界。

    Args:
        timeout_at: 持久化的 Delegation 超时时刻；为空表示未设置超时。
        now: 当前统一时钟值，由调用方提供，便于测试与事务内保持一致。

    Returns:
        bool: 已设置超时且当前时间大于等于超时时刻时返回 True。
    """
    return timeout_at is not None and now >= timeout_at
