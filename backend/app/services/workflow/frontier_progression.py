"""Durable Frontier -> Checkpoint -> Next Frontier 原子推进边界。

职责：在调用方事务内，将当前 Frontier 的成功结果固化为 Checkpoint，并幂等创建下一 Frontier。
边界：不负责 Planner 决策；next_identity 必须由调用方提供并保持确定性。
事务：本模块绝不 commit，当前 Frontier、Checkpoint、Next Frontier 必须在同一外层事务中提交。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier, transition_owned_frontier


async def complete_frontier_with_checkpoint(
    db: AsyncSession,
    *,
    frontier: WorkflowFrontier,
    worker_owner: str,
    attempt: int,
    checkpoint_state: dict,
    checkpoint_reason: str,
    node_id: str | None = None,
    node_attempt: int | None = None,
    node_status: str | None = None,
    input_data: dict | None = None,
    output_data: dict | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    next_identity: WorkflowFrontierIdentity | None = None,
    now: datetime,
) -> tuple[object, WorkflowFrontier | None]:
    """原子完成当前 Frontier、追加 Checkpoint，并幂等创建 Next Frontier。

    当前 Frontier 必须仍由 worker_owner/attempt 持有；任何 fencing mismatch 都会使外层事务回滚。
    next_identity 为 None 表示当前 Frontier 是终点，不创建后继 work item。
    """
    if next_identity is not None and next_identity.execution_id != frontier.execution_id:
        raise ValueError("Next Frontier 必须属于同一个 Workflow Execution")
    if next_identity is not None and next_identity.workflow_version_id != frontier.workflow_version_id:
        raise ValueError("Next Frontier 必须属于同一个 Workflow Version")

    checkpoint_service = WorkflowExecutionCheckpointService(db)
    checkpoint = await checkpoint_service.append_next_in_transaction(
        execution_id=frontier.execution_id,
        execution_status="running" if next_identity is not None else "completed",
        state_data=checkpoint_state,
        checkpoint_reason=checkpoint_reason,
        node_id=node_id,
        node_attempt=node_attempt,
        node_status=node_status,
        input_data=input_data,
        output_data=output_data,
        worker_owner=worker_owner,
        error_code=error_code,
        error_message=error_message,
        tenant_id=frontier.tenant_id,
    )

    completed = await transition_owned_frontier(
        db,
        frontier_id=frontier.id,
        worker_owner=worker_owner,
        attempt=attempt,
        target_status="completed",
        now=now,
    )

    next_frontier = None
    if next_identity is not None:
        next_frontier = await enqueue_frontier(
            db,
            tenant_id=frontier.tenant_id,
            identity=next_identity,
            node_ids=next_identity.node_ids,
            now=now,
        )

    return checkpoint, next_frontier
