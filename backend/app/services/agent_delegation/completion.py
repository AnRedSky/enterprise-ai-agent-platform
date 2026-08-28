"""Agent Delegation Worker 完成闭环。

职责：在当前 Worker Execution generation 仍有效时，将 Delegation 原子收敛为 completed 或 failed，并记录审计与 Trace。
边界：不执行 Runtime、不创建 Worker、不改变父 Workflow Execution；Worker generation 由 worker_execution_id 唯一标识。
关键依赖：AgentDelegation、WorkflowExecution、Delegation lifecycle、AuditLog、WorkflowTraceEvent。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_delegation import AgentDelegation
from app.models.core import AuditLog, utcnow_naive
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.agent_delegation.lifecycle import validate_transition, validate_worker_fence


async def _lock_delegation(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    delegation_id: UUID,
    worker_execution_id: UUID,
) -> tuple[AgentDelegation, WorkflowExecution]:
    """锁定 Delegation 与 Worker Execution，并验证 tenant/generation 关联。

    Args:
        db: 当前异步数据库会话。
        tenant_id: Delegation 所属租户。
        delegation_id: Delegation 标识。
        worker_execution_id: 当前 Worker generation 标识。

    Returns:
        tuple[AgentDelegation, WorkflowExecution]: 已锁定并通过租户边界校验的对象。

    Raises:
        HTTPException: Delegation 或 Worker Execution 不存在，或二者不属于同一租户/当前 generation。
    """
    delegation = (
        await db.execute(
            select(AgentDelegation)
            .where(
                AgentDelegation.id == delegation_id,
                AgentDelegation.tenant_id == tenant_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if delegation is None:
        raise HTTPException(404, "Agent Delegation 不存在")

    try:
        validate_worker_fence(
            status=delegation.status,
            worker_execution_id=delegation.worker_execution_id,
            expected_worker_execution_id=worker_execution_id,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    execution = (
        await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == worker_execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if execution is None:
        raise HTTPException(409, "当前 Worker Execution 不存在或跨 tenant")
    return delegation, execution


async def complete_delegation(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    delegation_id: UUID,
    worker_execution_id: UUID,
    output_data: dict | None = None,
) -> AgentDelegation:
    """以当前 Worker generation 原子完成 Delegation。

    Args:
        db: 当前异步数据库会话。
        tenant_id: Delegation 所属租户。
        delegation_id: Delegation 标识。
        worker_execution_id: 完成请求所属的 Worker Execution generation。
        output_data: Target Agent Runtime 的最终输出，可为空。

    Returns:
        AgentDelegation: 已进入 completed 的持久化 Delegation。

    Raises:
        HTTPException: generation 失效、Worker Execution 未完成或状态转换非法。

    事务边界：Delegation 状态、结果字段、AuditLog 与 Trace 在同一事务提交；父 Workflow Execution 不在本函数中改变。
    """
    delegation, execution = await _lock_delegation(
        db,
        tenant_id=tenant_id,
        delegation_id=delegation_id,
        worker_execution_id=worker_execution_id,
    )
    if execution.status != "completed":
        raise HTTPException(409, f"Worker Execution 当前状态为 {execution.status}，不能完成 Delegation")
    try:
        validate_transition(delegation.status, "completed")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    now = utcnow_naive()
    delegation.status = "completed"
    delegation.ended_at = now
    delegation.error_code = None
    delegation.error_message = None

    db.add(AuditLog(
        actor_id=execution.created_by,
        tenant_id=tenant_id,
        workflow_id=execution.workflow_id,
        workflow_version_id=execution.workflow_version_id,
        workflow_execution_id=delegation.source_execution_id,
        action="workflow.delegation.completed",
        resource_type="agent_delegation",
        resource_id=str(delegation.id),
        trace_id=delegation.trace_id,
        status="success",
        metadata_json={"worker_execution_id": str(worker_execution_id)},
    ))
    db.add(WorkflowTraceEvent(
        tenant_id=tenant_id,
        execution_id=delegation.source_execution_id,
        workflow_id=execution.workflow_id,
        workflow_version_id=execution.workflow_version_id,
        event_type="agent.delegation.completed",
        status="completed",
        trace_id=delegation.trace_id,
        actor_id=execution.created_by,
        data={"delegation_id": str(delegation.id), "worker_execution_id": str(worker_execution_id)},
    ))
    await db.commit()
    await db.refresh(delegation)
    return delegation


async def fail_delegation(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    delegation_id: UUID,
    worker_execution_id: UUID,
    error_code: str,
    error_message: str,
) -> AgentDelegation:
    """以当前 Worker generation 原子失败 Delegation。

    Args:
        db: 当前异步数据库会话。
        tenant_id: Delegation 所属租户。
        delegation_id: Delegation 标识。
        worker_execution_id: 失败请求所属的 Worker Execution generation。
        error_code: 稳定错误码。
        error_message: 面向运行审计的错误摘要。

    Returns:
        AgentDelegation: 已进入 failed 的持久化 Delegation。

    Raises:
        HTTPException: generation 失效、Worker Execution 状态不匹配或状态转换非法。

    事务边界：Delegation 失败状态、错误字段、AuditLog 与 Trace 在同一事务提交；父 Workflow Execution 不在本函数中改变。
    """
    delegation, execution = await _lock_delegation(
        db,
        tenant_id=tenant_id,
        delegation_id=delegation_id,
        worker_execution_id=worker_execution_id,
    )
    if execution.status != "failed":
        raise HTTPException(409, f"Worker Execution 当前状态为 {execution.status}，不能失败 Delegation")
    try:
        validate_transition(delegation.status, "failed")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    now = utcnow_naive()
    delegation.status = "failed"
    delegation.ended_at = now
    delegation.error_code = error_code[:100]
    delegation.error_message = error_message[:2000]

    db.add(AuditLog(
        actor_id=execution.created_by,
        tenant_id=tenant_id,
        workflow_id=execution.workflow_id,
        workflow_version_id=execution.workflow_version_id,
        workflow_execution_id=delegation.source_execution_id,
        action="workflow.delegation.failed",
        resource_type="agent_delegation",
        resource_id=str(delegation.id),
        trace_id=delegation.trace_id,
        status="failed",
        metadata_json={"worker_execution_id": str(worker_execution_id), "error_code": error_code[:100]},
    ))
    db.add(WorkflowTraceEvent(
        tenant_id=tenant_id,
        execution_id=delegation.source_execution_id,
        workflow_id=execution.workflow_id,
        workflow_version_id=execution.workflow_version_id,
        event_type="agent.delegation.failed",
        status="failed",
        trace_id=delegation.trace_id,
        actor_id=execution.created_by,
        data={
            "delegation_id": str(delegation.id),
            "worker_execution_id": str(worker_execution_id),
            "error_code": error_code[:100],
        },
    ))
    await db.commit()
    await db.refresh(delegation)
    return delegation
