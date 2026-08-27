"""Durable Frontier progression contract and atomic persistence boundary。

职责：在调用方事务内，将当前 Frontier 的成功结果固化为 Checkpoint，并幂等创建下一 Frontier。
边界：不负责 DAG Planner；next_identity 必须由调用方提供并保持确定性。
事务：本模块绝不 commit，当前 Frontier、Checkpoint、Next Frontier、Execution terminalization 必须在同一外层事务中提交。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

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
    *, frontier: WorkflowFrontier, next_identity: WorkflowFrontierIdentity | None, execution_status: str,
    checkpoint_reason: str = "frontier_completed", node_id: str | None = None, node_attempt: int | None = None,
    node_status: str | None = None, input_data: dict | None = None, output_data: dict | None = None,
) -> None:
    """在任何持久化动作前校验 Frontier progression 的最终一致性边界。"""
    if execution_status not in {"running", "completed"}:
        raise FrontierProgressionContractError(f"成功 Frontier 只能对应 running/completed Execution: {execution_status}")
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
    db: AsyncSession, *, frontier: WorkflowFrontier, worker_owner: str, checkpoint_state: dict,
    checkpoint_reason: str, next_identity: WorkflowFrontierIdentity | None,
) -> tuple[WorkflowExecutionCheckpoint, WorkflowFrontier | None] | None:
    """只根据 source Frontier 精确收敛重复 completion，禁止跨并行 Frontier 误认最新 Checkpoint。"""
    result = await db.execute(
        select(WorkflowFrontier).where(
            WorkflowFrontier.id == frontier.id, WorkflowFrontier.tenant_id == frontier.tenant_id,
        ).with_for_update()
    )
    current = result.scalar_one_or_none()
    if current is None or current.status != "completed":
        return None

    checkpoint_result = await db.execute(
        select(WorkflowExecutionCheckpoint).where(
            WorkflowExecutionCheckpoint.execution_id == current.execution_id,
            WorkflowExecutionCheckpoint.frontier_id == current.id,
            WorkflowExecutionCheckpoint.checkpoint_reason == checkpoint_reason,
        ).order_by(WorkflowExecutionCheckpoint.sequence.desc()).limit(1)
    )
    checkpoint = checkpoint_result.scalar_one_or_none()
    if checkpoint is None:
        raise FrontierProgressionContractError("已完成 Frontier 缺少绑定 source Frontier 的 completion Checkpoint，拒绝再次 completion")
    if checkpoint.state_data != checkpoint_state or checkpoint.worker_owner != worker_owner:
        raise FrontierProgressionContractError("重复 completion 的 Checkpoint payload 与既有 Durable fact 不一致")

    next_frontier = None
    if next_identity is not None:
        next_result = await db.execute(
            select(WorkflowFrontier).where(
                WorkflowFrontier.tenant_id == current.tenant_id,
                WorkflowFrontier.frontier_key == next_identity.key(),
            )
        )
        next_frontier = next_result.scalar_one_or_none()
        if next_frontier is None:
            raise FrontierProgressionContractError("已完成 Frontier 缺少既有 Next Frontier，拒绝生成第二条 completion fact")
        if next_frontier.execution_id != current.execution_id:
            raise FrontierProgressionContractError("既有 Next Frontier 不属于当前 Workflow Execution")
        if next_frontier.workflow_version_id != current.workflow_version_id:
            raise FrontierProgressionContractError("既有 Next Frontier 不属于当前 Workflow Version")

    return checkpoint, next_frontier


async def complete_frontier_with_checkpoint(
    db: AsyncSession, *, frontier: WorkflowFrontier, worker_owner: str, attempt: int, checkpoint_state: dict,
    checkpoint_reason: str, node_id: str | None = None, node_attempt: int | None = None,
    node_status: str | None = None, input_data: dict | None = None, output_data: dict | None = None,
    error_code: str | None = None, error_message: str | None = None,
    next_identity: WorkflowFrontierIdentity | None = None, now: datetime, actor_id: UUID | None = None,
) -> tuple[WorkflowExecutionCheckpoint, WorkflowFrontier | None]:
    """原子完成当前 Frontier、追加 Checkpoint、Terminalize Execution 并幂等创建 Next Frontier。

    `attempt` 只代表当前 Frontier consumption attempt；Execution 的 `worker_attempt` 是独立的
    Worker ownership epoch。两者必须分别校验，禁止用 Frontier attempt 充当 Execution fencing generation。
    """
    execution_status = "running" if next_identity is not None else "completed"
    validate_frontier_progression_contract(
        frontier=frontier, next_identity=next_identity, execution_status=execution_status,
        checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt,
        node_status=node_status, input_data=input_data, output_data=output_data,
    )
    existing = await _resolve_completed_frontier_idempotency(
        db, frontier=frontier, worker_owner=worker_owner, checkpoint_state=checkpoint_state,
        checkpoint_reason=checkpoint_reason, next_identity=next_identity,
    )
    if existing is not None:
        return existing

    execution_result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == frontier.execution_id,
            WorkflowExecution.tenant_id == frontier.tenant_id,
        ).with_for_update()
    )
    execution = execution_result.scalar_one_or_none()
    if execution is None:
        raise FrontierProgressionContractError("Frontier 对应的 Workflow Execution 不存在")
    execution_worker_attempt = int(execution.worker_attempt or 0)
    if execution.worker_owner != worker_owner:
        raise FrontierProgressionContractError("Execution Worker ownership 已失效")
    if execution.worker_lease_expires_at is None or execution.worker_lease_expires_at <= now:
        raise FrontierProgressionContractError("Execution Worker lease 已失效")

    await transition_owned_frontier(
        db, frontier_id=frontier.id, worker_owner=worker_owner, attempt=attempt,
        target_status="completed", now=now,
    )

    if next_identity is None:
        if execution.status != "running":
            raise FrontierProgressionContractError(f"终态 Frontier 只能从 running Execution 收敛: {execution.status}")
        if execution_worker_attempt != int(execution.worker_attempt or 0):
            raise FrontierProgressionContractError("Execution Worker fencing generation 在事务内发生变化")
        execution.status = "completed"
        execution.ended_at = now
        execution.current_node_id = None
        execution.output_data = dict(checkpoint_state)
        execution.worker_owner = None
        execution.worker_lease_expires_at = None
        audit_actor = actor_id or execution.created_by
        governance = WorkflowGovernanceService(db)
        await governance.trace(
            execution, audit_actor, "execution.state_changed", "completed",
            data={"from": "running", "to": "completed", "frontier_id": str(frontier.id)},
        )
        await governance.audit(
            execution, audit_actor, "workflow.execution.completed", "success",
            metadata={"frontier_id": str(frontier.id)},
        )

    checkpoint_service = WorkflowExecutionCheckpointService(db)
    checkpoint = await checkpoint_service.append_next_in_transaction(
        execution_id=frontier.execution_id, execution_status=execution_status, state_data=checkpoint_state,
        checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt, node_status=node_status,
        input_data=input_data, output_data=output_data, worker_owner=worker_owner, error_code=error_code,
        error_message=error_message, tenant_id=frontier.tenant_id,
        expected_worker_owner=worker_owner,
        expected_worker_attempt=execution_worker_attempt,
        frontier_id=frontier.id if checkpoint_reason == "frontier_completed" else None,
    )

    next_frontier = None
    if next_identity is not None:
        next_frontier = await enqueue_frontier(
            db, tenant_id=frontier.tenant_id, identity=next_identity, node_ids=next_identity.node_ids, now=now,
        )
    return checkpoint, next_frontier
