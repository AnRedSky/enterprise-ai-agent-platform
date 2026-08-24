"""Workflow Execution 领域服务。

职责：管理 Workflow Execution 与 Node Execution 状态机、幂等创建、重试、取消及 Runtime 执行入口。
边界：不负责 Workflow Registry 生命周期、不复制 Runtime 节点执行算法；节点执行统一委托 WorkflowRuntime。
关键依赖：Workflow/Execution ORM、WorkflowRuntime、WorkflowGovernanceService 与 Workflow Runtime CircuitBreaker。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.runtime.workflow.circuit_breaker import CircuitOpenError
from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow.governance import WorkflowGovernanceService


class WorkflowExecutionService:
    """Workflow Execution 状态机与 Runtime 执行领域服务。"""

    EXECUTION_STATES = {"pending", "running", "completed", "failed", "cancelled"}
    NODE_STATES = {"pending", "running", "completed", "failed", "skipped"}
    TERMINAL_EXECUTION_STATES = {"completed", "failed", "cancelled"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.governance = WorkflowGovernanceService(db)

    async def create(self, workflow: Workflow, version: WorkflowVersion, actor_id: UUID, input_data: dict,
                     idempotency_key: str | None = None) -> WorkflowExecution:
        if workflow.published_version_id != version.id or version.status != "published":
            raise HTTPException(409, "只能执行当前已发布版本")
        WorkflowRuntime.validate_definition(version.definition)
        workflow_id = workflow.id
        workflow_version_id = version.id
        tenant_id = workflow.tenant_id
        if idempotency_key:
            existing = (await self.db.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id,
                WorkflowExecution.idempotency_key == idempotency_key,
            ))).scalar_one_or_none()
            if existing is not None:
                if existing.workflow_id != workflow_id or existing.workflow_version_id != workflow_version_id:
                    raise HTTPException(409, "Idempotency-Key 已用于其他 Workflow Execution")
                return existing
        execution = WorkflowExecution(
            tenant_id=tenant_id, workflow_id=workflow_id, workflow_version_id=workflow_version_id,
            created_by=actor_id, idempotency_key=idempotency_key, status="pending", input_data=input_data,
        )
        try:
            if idempotency_key:
                async with self.db.begin_nested():
                    self.db.add(execution)
                    await self.db.flush()
            else:
                self.db.add(execution)
                await self.db.flush()
        except IntegrityError:
            if not idempotency_key:
                raise
            existing = (await self.db.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.idempotency_key == idempotency_key,
            ))).scalar_one_or_none()
            if existing is None:
                raise
            if existing.workflow_id != workflow_id or existing.workflow_version_id != workflow_version_id:
                raise HTTPException(409, "Idempotency-Key 已用于其他 Workflow Execution")
            return existing
        await self.governance.audit(execution, actor_id, "workflow.execution.created", "success")
        await self.governance.trace(execution, actor_id, "execution.created", "pending", data={
            "input_keys": sorted(input_data.keys()), "idempotency_key_present": idempotency_key is not None,
        })
        return execution
