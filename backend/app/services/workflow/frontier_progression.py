"""Durable Frontier progression contract and atomic persistence boundary。

职责：在调用方事务内，将当前 Frontier 的成功结果固化为 Checkpoint，并幂等创建下一 Frontier。
边界：不负责 DAG Planner；next_identity 必须由调用方提供并保持确定性。
事务：本模块绝不 commit，当前 Frontier、Checkpoint、Next Frontier、Execution terminalization 必须在同一外层事务中提交。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier, transition_owned_frontier
from app.services.workflow.governance import WorkflowGovernanceService


class FrontierProgressionContractError(ValueError):
    """表示 Frontier → Checkpoint → Next Frontier 违反 Durable contract。"""


def validate_frontier_progression_contract(
    *,
    frontier: WorkflowFrontier,
    next_identity: WorkflowFrontierIdentity | None,
    execution_status: str,
    checkpoint_reason: str = "frontier_completed",
    node_id: str | None = None,
    node_attempt: int | None = None,
    node_status: str | None = None,
    input_data: dict | None = None,
    output_data: dict | None = None,
) -> None:
    """在任何持久化动作前校验 Frontier progression 的最终一致性边界。"""
    if execution_status not in {"running", "completed"}:
        raise FrontierProgressionContractError(
            f"成功 Frontier 只能对应 running/completed Execution: {execution_status}"
        )
    if checkpoint_reason == "frontier_completed" and any(
        value is not None for value in (node_id, node_attempt, node_status, input_data, output_data)
    ):
        raise FrontierProgressionContractError(
            "frontier_completed 只能生成 Execution-level Checkpoint，不得携带 Node identity/status/input/output"
        )
    if next_identity is None:
        if execution_status != "completed":
            raise FrontierProgressionContractError("没有 Next Frontier 时 Execution 必须进入 completed")
        return
    if execution_status != "running":
        raise FrontierProgressionContractError("存在 Next Frontier 时 Execution 必须保持 running")
    if next_identity.execution_id != frontier.execution_id:
        raise FrontierProgressionContractError("Next Frontier 必须属于同一个 Workflow Execution")
    if next_identity.workflow_version_id != frontier.workflow_version_id:
        raise FrontierProgressionContractError("Next Frontier 必须属于同一个 Workflow Version")
    if not next_identity.node_ids:
        raise FrontierProgressionContractError("Next Frontier 至少需要一个 Node")
    if next_identity.key() == frontier.frontier_key:
        raise FrontierProgressionContractError("Next Frontier identity 不能与当前 Frontier 相同")


async def _resolve_completed_frontier_idempotency(
    db: AsyncSession,
    *,
    frontier: WorkflowFrontier,
    worker_owner: str,
    checkpoint_state: dict,
    checkpoint_reason: str,
    next_identity: WorkflowFrontierIdentity | None,
) -> tuple[WorkflowExecutionCheckpoint, WorkflowFrontier | None] | None:
    """在重复 completion 已经提交后收敛到既有 Durable facts。

    该边界只接受已经完整提交的 completion：当前 Frontier 必须为 completed，且对应
    `frontier_completed` Checkpoint 必须存在并与本次 state/owner/reason 一致；存在 Next Frontier
    时还必须已经能按确定性 identity 找到后继 Frontier。任何缺失都视为事务完整性破坏，而不是
    静默创建第二套 durable fact。
    """
    result = await db.execute(
        select(WorkflowFrontier)
        .where(
            WorkflowFrontier.id == frontier.id,
            WorkflowFrontier.tenant_id == frontier.tenant_id,
        )
        .with_for_update()
    )
    current = result.scalar_one_or_none()
    if current is None or current.status != "completed":
        return None

    checkpoint_result = await db.execute(
        select(WorkflowExecutionCheckpoint)
        .where(
            WorkflowExecutionCheckpoint.execution_id == current.execution_id,
            WorkflowExecutionCheckpoint.checkpoint_reason == checkpoint_reason,
        )
        .order_by(WorkflowExecutionCheckpoint.sequence.desc())
        .limit(1)
    )
    checkpoint = checkpoint_result.scalar_one_or_none()
    if checkpoint is None:
        raise FrontierProgressionContractError(
            "已完成 Frontier 缺少对应 completion Checkpoint，拒绝再次 completion"
        )
    if checkpoint.state_data != checkpoint_state or checkpoint.worker_owner != worker_owner:
        raise FrontierProgressionContractError(
            "重复 completion 的 Checkpoint payload 与既有 Durable fact 不一致"
        )

    next_frontier = None
    if next_identity is not None:
        next_result = await db.execute(
            select(WorkflowFrontier)
            .where(
                WorkflowFrontier.tenant_id == current.tenant_id,
                WorkflowFrontier.frontier_key == next_identity.key(),
            )
        )
        next_frontier = next_result.scalar_one_or_none()
        if next_frontier is None:
            raise FrontierProgressionContractError(
                "已完成 Frontier 缺少既有 Next Frontier，拒绝生成第二条 completion fact"
            )
        if next_frontier.execution_id != current.execution_id:
            raise FrontierProgressionContractError("既有 Next Frontier 不属于当前 Workflow Execution")
        if next_frontier.workflow_version_id != current.workflow_version_id:
            raise FrontierProgressionContractError("既有 Next Frontier 不属于当前 Workflow Version")

    return checkpoint, next_frontier


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
    actor_id: UUID | None = None,
) -> tuple[WorkflowExecutionCheckpoint, WorkflowFrontier | None]:
    """原子完成当前 Frontier、追加 Checkpoint、Terminalize Execution 并幂等创建 Next Frontier。

    事务边界：锁定并修改当前 Frontier、终态 Execution、追加 Checkpoint、幂等创建 Next Frontier，均不 commit。
    对已经提交的重复 completion，若既有 Durable facts 完整且 payload 一致，则返回既有事实而不产生第二条记录。
    """
    execution_status = "running" if next_identity is not None else "completed"
    validate_frontier_progression_contract(
        frontier=frontier,
        next_identity=next_identity,
        execution_status=execution_status,
        checkpoint_reason=checkpoint_reason,
        node_id=node_id,
        node_attempt=node_attempt,
        node_status=node_status,
        input_data=input_data,
        output_data=output_data,
    )

    # Duplicate completion 可能来自旧 Worker 的 retry / HTTP replay。先检查已提交的
    # completed Frontier；只有完整 Durable facts 且 payload 一致时才返回既有结果。
    existing = await _resolve_completed_frontier_idempotency(
        db,
        frontier=frontier,
        worker_owner=worker_owner,
        checkpoint_state=checkpoint_state,
        checkpoint_reason=checkpoint_reason,
        next_identity=next_identity,
    )
    if existing is not None:
        return existing

    await transition_owned_frontier(
        db,
        frontier_id=frontier.id,
        worker_owner=worker_owner,
        attempt=attempt,
        target_status="completed",
        now=now,
    )

    if next_identity is None:
        execution_result = await db.execute(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.id == frontier.execution_id,
                WorkflowExecution.tenant_id == frontier.tenant_id,
            )
            .with_for_update()
        )
        execution = execution_result.scalar_one_or_none()
        if execution is None:
            raise FrontierProgressionContractError("Frontier 对应的 Workflow Execution 不存在")
        if execution.status != "running":
            raise FrontierProgressionContractError(
                f"终态 Frontier 只能从 running Execution 收敛: {execution.status}"
            )
        if execution.worker_owner != worker_owner or int(execution.worker_attempt or 0) != attempt:
            raise FrontierProgressionContractError("Execution Worker ownership 或 fencing generation 已失效")

        execution.status = "completed"
        execution.ended_at = now
        execution.current_node_id = None
        execution.output_data = dict(checkpoint_state)
        execution.worker_owner = None
        execution.worker_lease_expires_at = None
        audit_actor = actor_id or execution.created_by
        governance = WorkflowGovernanceService(db)
        await governance.trace(
            execution,
            audit_actor,
            "execution.state_changed",
            "completed",
            data={"from": "running", "to": "completed", "frontier_id": str(frontier.id)},
        )
        await governance.audit(
            execution,
            audit_actor,
            "workflow.execution.completed",
            "success",
            metadata={"frontier_id": str(frontier.id)},
        )

    checkpoint_service = WorkflowExecutionCheckpointService(db)
    checkpoint = await checkpoint_service.append_next_in_transaction(
        execution_id=frontier.execution_id,
        execution_status=execution_status,
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
        expected_worker_owner=worker_owner if next_identity is not None else None,
        expected_worker_attempt=attempt if next_identity is not None else None,
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
