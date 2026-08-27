"""Durable Frontier progression contract and atomic persistence boundary.

职责：在调用方事务内，将当前 Frontier 的成功结果固化为 Checkpoint，并幂等创建下一 Frontier。
边界：不负责 DAG Planner；next_identity 必须由调用方提供并保持确定性。
事务：本模块绝不 commit，当前 Frontier、Checkpoint、Next Frontier 必须在同一外层事务中提交。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowFrontier
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier, transition_owned_frontier


class FrontierProgressionContractError(ValueError):
    """表示 Frontier → Checkpoint → Next Frontier 违反 Durable contract。"""


def validate_frontier_progression_contract(
    *,
    frontier: WorkflowFrontier,
    next_identity: WorkflowFrontierIdentity | None,
    execution_status: str,
) -> None:
    """在任何持久化动作前校验 Frontier progression 的最终一致性边界。

    成功的非终态 Frontier 必须产生同一 Execution/Version 的 Next Frontier；终态 Frontier
    必须同时把 Execution 视为 completed。禁止把当前 Frontier 自己作为 Next Frontier，避免
    唯一键幂等机制把已完成 work item 重新排回队列。
    """
    if execution_status not in {"running", "completed"}:
        raise FrontierProgressionContractError(
            f"成功 Frontier 只能对应 running/completed Execution: {execution_status}"
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
) -> tuple[WorkflowExecutionCheckpoint, WorkflowFrontier | None]:
    """原子完成当前 Frontier、追加 Checkpoint，并幂等创建 Next Frontier。

    锁顺序固定为 Frontier -> Execution/Checkpoint -> Next Frontier，避免与 Worker Claim
    的 Frontier -> Execution 锁顺序产生数据库死锁风险。任何后续步骤失败都由调用方回滚。
    """
    execution_status = "running" if next_identity is not None else "completed"
    validate_frontier_progression_contract(
        frontier=frontier,
        next_identity=next_identity,
        execution_status=execution_status,
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

    # 第三阶段：后继 Frontier 使用确定性 identity 幂等创建；冲突时收敛到已有记录。
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
