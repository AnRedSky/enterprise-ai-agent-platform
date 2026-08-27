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
    """在任何持久化动作前校验 Frontier progression 的最终一致性边界。

    成功的非终态 Frontier 必须产生同一 Execution/Version 的 Next Frontier；终态 Frontier
    必须同时把 Execution 视为 completed。`frontier_completed` 是 Execution-level snapshot，
    不允许携带 Node identity、Node status 或 Node I/O，避免把两个 durable fact 层级混合到一条快照中。

    Args:
        frontier: 当前需要完成的 Durable Frontier。
        next_identity: 下一 Frontier 的确定性 identity；终态完成时为 None。
        execution_status: 本次 completion 对应的 Execution 状态。
        checkpoint_reason: Checkpoint 原因；`frontier_completed` 使用 Execution-level contract。
        node_id: 可选 Node identity，仅 Node-level Checkpoint 原因允许使用。
        node_attempt: 可选 Node attempt，仅 Node-level Checkpoint 原因允许使用。
        node_status: 可选 Node 状态，仅 Node-level Checkpoint 原因允许使用。
        input_data: 可选 Node 输入，仅 Node-level Checkpoint 原因允许使用。
        output_data: 可选 Node 输出，仅 Node-level Checkpoint 原因允许使用。

    Raises:
        FrontierProgressionContractError: Frontier、Execution 或 Checkpoint 层级不满足原子推进约束。
    """
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
            raise FrontierProgressionContractError(
                "没有 Next Frontier 时 Execution 必须进入 completed"
            )
        return
    if execution_status != "running":
        raise FrontierProgressionContractError(
            "存在 Next Frontier 时 Execution 必须保持 running"
        )
    if next_identity.execution_id != frontier.execution_id:
        raise FrontierProgressionContractError("Next Frontier 必须属于同一个 Workflow Execution")
    if next_identity.workflow_version_id != frontier.workflow_version_id:
        raise FrontierProgressionContractError("Next Frontier 必须属于同一个 Workflow Version")
    if not next_identity.node_ids:
        raise FrontierProgressionContractError("Next Frontier 至少需要一个 Node")
    if next_identity.key() == frontier.frontier_key:
        raise FrontierProgressionContractError("Next Frontier identity 不能与当前 Frontier 相同")


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

    Args:
        db: 当前事务数据库会话。
        frontier: 当前需要完成的 Durable Frontier。
        worker_owner: 当前 Worker ownership 标识。
        attempt: 当前 fencing generation。
        checkpoint_state: Execution-level completion 快照状态。
        checkpoint_reason: Checkpoint 原因。
        node_id: Node-level Checkpoint 的节点身份；`frontier_completed` 时必须为空。
        node_attempt: Node-level Checkpoint 的节点 attempt；`frontier_completed` 时必须为空。
        node_status: Node-level Checkpoint 的节点状态；`frontier_completed` 时必须为空。
        input_data: Node-level Checkpoint 输入；`frontier_completed` 时必须为空。
        output_data: Node-level Checkpoint 输出；`frontier_completed` 时必须为空。
        error_code: 可选错误码。
        error_message: 可选错误信息。
        next_identity: 下一 Frontier 的确定性 identity。
        now: 当前时间。
        actor_id: Execution terminalization 审计主体；未提供时使用 Execution created_by。

    Returns:
        `(Checkpoint, Next Frontier)`；终态 Frontier 的 Next Frontier 为 None。

    Raises:
        FrontierProgressionContractError: progression contract 不满足。
        HTTPException: Execution 已经不是 running 或 Worker fencing 已失效。

    事务边界：锁定并修改当前 Frontier、追加 Checkpoint、终态 Execution、幂等创建 Next Frontier，均不 commit；调用方统一提交或 rollback。
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

    # 第一阶段：先验证并锁定当前 Frontier。只有当前 fencing generation 仍有效，
    # 才允许写入 Checkpoint；因此 stale Worker 不会产生新的持久化事实。
    await transition_owned_frontier(
        db,
        frontier_id=frontier.id,
        worker_owner=worker_owner,
        attempt=attempt,
        target_status="completed",
        now=now,
    )

    # 第二阶段：同一事务中追加不可变 Checkpoint。Checkpoint Service 会锁定 Execution，
    # 并串行分配 sequence，同时再次校验 Execution owner/generation，形成第二道 Durable 写入防线。
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
        expected_worker_owner=worker_owner,
        expected_worker_attempt=attempt,
    )

    # 第三阶段：终态 Frontier 必须在同一事务内同步 terminalize Execution。
    # 不能调用带 commit 的通用 transition，否则会在 Next Frontier/Checkpoint 尚未完成时提前提交事务。
    if next_identity is None:
        execution_query = (
            select(WorkflowExecution)
            .where(
                WorkflowExecution.id == frontier.execution_id,
                WorkflowExecution.tenant_id == frontier.tenant_id,
            )
            .with_for_update()
        )
        execution_result = await db.execute(execution_query)
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

    # 第四阶段：后继 Frontier 使用确定性 identity 幂等创建；冲突时收敛到已有记录。
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
