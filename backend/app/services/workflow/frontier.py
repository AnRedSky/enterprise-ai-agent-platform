"""Workflow Frontier 领域契约。

职责：定义 Durable DAG Frontier 的稳定身份、状态转换和可调度边界。
边界：只负责确定性领域规则，不直接访问数据库、Scheduler 或 Worker。
关键依赖：Python 标准库 uuid、dataclasses。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from uuid import UUID


class WorkflowFrontierStatus(StrEnum):
    """Frontier 的持久化生命周期状态。"""

    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_WAIT = "retry_wait"


@dataclass(frozen=True)
class WorkflowFrontierIdentity:
    """Durable Frontier 的确定性身份。"""

    execution_id: UUID
    workflow_version_id: UUID
    decision_fingerprint: str
    node_ids: tuple[str, ...]

    def key(self) -> str:
        """生成稳定 Frontier 幂等键。

        Returns:
            基于执行、版本、Decision fingerprint 与规范化 Node 集合生成的 SHA-256 键。

        设计意图：Frontier 的 Node 集合表示同一个可并行执行边界，集合顺序不应因为 Planner、
        Resume 或并发重建时的遍历顺序变化而生成第二个 Durable Frontier；真正需要保留的执行顺序
        仍由 `node_ids` 原值交给 Executor，而不是由 identity key 承担。
        """
        canonical_node_ids = tuple(sorted(self.node_ids))
        payload = "|".join(
            (
                str(self.execution_id),
                str(self.workflow_version_id),
                self.decision_fingerprint,
                ",".join(canonical_node_ids),
            )
        ).encode("utf-8")
        return f"frontier:{sha256(payload).hexdigest()}"


@dataclass(frozen=True)
class WorkflowFrontierTransition:
    """Frontier 状态转换结果。"""

    source: WorkflowFrontierStatus
    target: WorkflowFrontierStatus


_ALLOWED_TRANSITIONS = {
    WorkflowFrontierStatus.PENDING: frozenset({WorkflowFrontierStatus.CLAIMED}),
    WorkflowFrontierStatus.CLAIMED: frozenset({WorkflowFrontierStatus.RUNNING, WorkflowFrontierStatus.RETRY_WAIT, WorkflowFrontierStatus.FAILED}),
    WorkflowFrontierStatus.RUNNING: frozenset({WorkflowFrontierStatus.COMPLETED, WorkflowFrontierStatus.RETRY_WAIT, WorkflowFrontierStatus.FAILED}),
    WorkflowFrontierStatus.RETRY_WAIT: frozenset({WorkflowFrontierStatus.CLAIMED, WorkflowFrontierStatus.FAILED}),
    WorkflowFrontierStatus.COMPLETED: frozenset(),
    WorkflowFrontierStatus.FAILED: frozenset(),
}


def transition_frontier(status: WorkflowFrontierStatus, target: WorkflowFrontierStatus) -> WorkflowFrontierTransition:
    """校验 Frontier 生命周期转换。

    Args:
        status: 当前 Frontier 状态。
        target: 请求进入的目标状态。

    Returns:
        合法的 Frontier 状态转换。

    Raises:
        ValueError: 状态转换不符合 Frontier 生命周期。

    设计意图：Claim、Retry 与 Terminal 状态必须形成有限状态机，避免 Worker 通过重复领取或过期租约把已完成 Frontier 重新推进。
    """
    if target not in _ALLOWED_TRANSITIONS[status]:
        raise ValueError(f"非法 Frontier 状态转换: {status.value} -> {target.value}")
    return WorkflowFrontierTransition(source=status, target=target)
