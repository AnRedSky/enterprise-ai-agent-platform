"""Durable Frontier retry policy and scheduling primitives.

职责：将可重试失败转换为 Durable Frontier 的 retry_wait 状态和下一次 available_at。
边界：不创建新的 WorkflowExecution，不执行 commit；调用方拥有事务。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier
from app.services.workflow.frontier_repository import transition_owned_frontier


@dataclass(frozen=True, slots=True)
class FrontierRetryPolicy:
    """确定性、无外部副作用的 Frontier retry policy。"""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")

    def can_retry(self, attempt: int) -> bool:
        """attempt 是当前已成功 Claim 的 fencing generation。"""
        return 0 < attempt < self.max_attempts

    def delay_seconds(self, attempt: int) -> float:
        """按当前 attempt 计算指数退避，并限制最大延迟。"""
        if attempt < 1:
            raise ValueError("attempt must be positive")
        return min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))


async def schedule_frontier_retry(
    db: AsyncSession,
    *,
    frontier: WorkflowFrontier,
    worker_owner: str,
    attempt: int,
    now: datetime,
    error_code: str,
    error_message: str,
    policy: FrontierRetryPolicy,
) -> WorkflowFrontier:
    """将当前 Worker 持有的 Frontier 安排为 Durable retry 或终态失败。

    Retry 不创建新的 Execution/Frontier；同一 Frontier 通过 retry_wait + available_at
    再次进入 Claim，下一次 Claim 才产生新的 fencing generation。
    """
    if not error_code:
        raise ValueError("error_code must not be empty")
    frontier.error_code = error_code
    frontier.error_message = error_message
    if not policy.can_retry(attempt):
        return await transition_owned_frontier(
            db,
            frontier_id=frontier.id,
            worker_owner=worker_owner,
            attempt=attempt,
            target_status="failed",
            now=now,
        )

    delay = policy.delay_seconds(attempt)
    frontier.available_at = now + timedelta(seconds=delay)
    frontier.completed_at = None
    await transition_owned_frontier(
        db,
        frontier_id=frontier.id,
        worker_owner=worker_owner,
        attempt=attempt,
        target_status="retry_wait",
        now=now,
    )
    return frontier
