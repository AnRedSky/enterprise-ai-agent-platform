"""Agent Delegation 原子 Claim。

职责：在现有 WorkflowExecution Worker ownership 体系上，把 pending Delegation 原子地认领为 running。
边界：不执行 Agent Runtime，不实现第二套 lease/retry/recovery；Worker ownership 复用 WorkflowExecution 的 worker_owner 与 worker_lease_expires_at。
关键依赖：PostgreSQL 行锁、AgentDelegation、WorkflowExecution、Delegation lifecycle 规则。
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_delegation import AgentDelegation
from app.models.core import AuditLog, utcnow_naive
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.agent_delegation.lifecycle import is_timeout_due, validate_transition


async def claim_delegation(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    delegation_id: UUID,
    worker_owner: str,
) -> AgentDelegation:
    """原子认领一个 pending Delegation，并创建对应的 Workflow Worker Execution。

    Args:
        db: 当前事务使用的异步数据库会话。
        tenant_id: Delegation 所属租户，用于强制 tenant boundary。
        delegation_id: 待认领 Delegation 标识。
        worker_owner: Worker 实例唯一标识，写入既有 WorkflowExecution ownership 字段。

    Returns:
        AgentDelegation: 已从 pending 转为 running 且绑定唯一 worker_execution_id 的 Delegation。

    Raises:
        HTTPException: Delegation 不存在、已经被其他 Worker 认领、已取消/终态、已超时或 Worker 标识无效。

    设计意图：`SELECT ... FOR UPDATE` 锁住 Delegation 行；所有竞争 Worker 在同一行上串行判断，只有第一个仍为 pending 的事务能够创建 WorkflowExecution 并写入 worker_execution_id。整个 Claim 与 Worker Execution 创建在同一数据库事务中提交，因此不会出现 Delegation 已 running 但 Worker Execution 未持久化的半完成状态。
    """
    owner = worker_owner.strip()
    if not owner or len(owner) > 128:
        raise HTTPException(422, "worker_owner 必须为 1-128 个字符")

    item = (
        await db.execute(
            select(AgentDelegation)
            .where(
                AgentDelegation.id == delegation_id,
                AgentDelegation.tenant_id == tenant_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "Agent Delegation 不存在")

    now = utcnow_naive()
    if item.status != "pending":
        raise HTTPException(409, f"Delegation 当前状态为 {item.status}，不能再次 Claim")
    if is_timeout_due(item.timeout_at, now=now):
        raise HTTPException(409, "Delegation 已达到 timeout 边界，拒绝 Claim")
    try:
        validate_transition(item.status, "running")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    source = (
        await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == item.source_execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(409, "Delegation source Workflow Execution 不存在")
    if source.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(409, "父 Workflow Execution 已进入终态，拒绝 Claim")

    worker_execution = WorkflowExecution(
        tenant_id=tenant_id,
        workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id,
        created_by=source.created_by,
        idempotency_key=f"delegation:{item.id}",
        status="running",
        current_node_id=None,
        input_data=dict(item.input_data),
        started_at=now,
        worker_owner=owner,
        worker_lease_expires_at=now + timedelta(seconds=item.timeout_seconds),
        worker_attempt=1,
    )
    db.add(worker_execution)
    await db.flush()

    item.status = "running"
    item.worker_execution_id = worker_execution.id
    item.started_at = now

    db.add(AuditLog(
        actor_id=source.created_by,
        tenant_id=tenant_id,
        workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id,
        workflow_execution_id=source.id,
        action="workflow.delegation.claimed",
        resource_type="agent_delegation",
        resource_id=str(item.id),
        trace_id=item.trace_id,
        status="success",
        metadata_json={
            "worker_execution_id": str(worker_execution.id),
            "worker_owner": owner,
            "target_agent_version_id": str(item.target_agent_version_id),
        },
    ))
    db.add(WorkflowTraceEvent(
        tenant_id=tenant_id,
        execution_id=source.id,
        workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id,
        event_type="agent.delegation.claimed",
        status="running",
        trace_id=item.trace_id,
        actor_id=source.created_by,
        data={
            "delegation_id": str(item.id),
            "worker_execution_id": str(worker_execution.id),
            "target_agent_version_id": str(item.target_agent_version_id),
        },
    ))

    await db.commit()
    await db.refresh(item)
    return item
