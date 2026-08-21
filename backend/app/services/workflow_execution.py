from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow_governance import WorkflowGovernanceService
from app.services.circuit_breaker import CircuitOpenError


class WorkflowExecutionService:
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
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
            created_by=actor_id,
            idempotency_key=idempotency_key,
            status="pending",
            input_data=input_data,
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
                WorkflowExecution.tenant_id == tenant_id,
                WorkflowExecution.idempotency_key == idempotency_key,
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
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, admin: bool = False) -> WorkflowExecution:
        query = select(WorkflowExecution).where(WorkflowExecution.id == execution_id, WorkflowExecution.tenant_id == tenant_id)
        if not admin:
            query = query.where(WorkflowExecution.created_by == actor_id)
        execution = (await self.db.execute(query)).scalar_one_or_none()
        if execution is None:
            raise HTTPException(404, "Workflow Execution 不存在")
        return execution

    async def nodes(self, execution: WorkflowExecution) -> list[WorkflowNodeExecution]:
        result = await self.db.execute(select(WorkflowNodeExecution).where(
            WorkflowNodeExecution.execution_id == execution.id
        ).order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc()))
        return list(result.scalars().all())

    async def trace(self, execution: WorkflowExecution) -> list[WorkflowTraceEvent]:
        result = await self.db.execute(select(WorkflowTraceEvent).where(
            WorkflowTraceEvent.execution_id == execution.id, WorkflowTraceEvent.tenant_id == execution.tenant_id
        ).order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc()))
        return list(result.scalars().all())

    async def _lock_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Reload the execution under a row lock before changing its state."""
        if not isinstance(self.db, AsyncSession):
            return execution
        locked = (await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution.id)
            .with_for_update()
        )).scalar_one_or_none()
        if locked is None:
            raise HTTPException(404, "Workflow Execution 不存在")
        return locked

    async def transition(self, execution: WorkflowExecution, target_status: str, node_id: str | None = None,
                         error_code: str | None = None, error_message: str | None = None,
                         output_data: dict | None = None, actor_id: UUID | None = None) -> WorkflowExecution:
        if target_status not in self.EXECUTION_STATES:
            raise HTTPException(400, "不支持的 Execution 状态")
        execution = await self._lock_execution(execution)
        current = execution.status
        allowed = {"pending": {"running", "cancelled"}, "running": {"completed", "failed", "cancelled"},
                   "completed": set(), "failed": set(), "cancelled": set()}
        if target_status not in allowed[current]:
            raise HTTPException(409, f"Execution 不允许从 {current} 转换到 {target_status}")
        now = datetime.now(UTC).replace(tzinfo=None)
        execution.status = target_status
        if node_id is not None:
            execution.current_node_id = node_id
        if output_data is not None:
            execution.output_data = output_data
        if error_code is not None:
            execution.error_code = error_code
        if error_message is not None:
            execution.error_message = error_message
        if target_status == "running" and execution.started_at is None:
            execution.started_at = now
        if target_status in self.TERMINAL_EXECUTION_STATES:
            execution.ended_at = now
            execution.current_node_id = None
        audit_actor = actor_id or execution.created_by
        await self.governance.trace(execution, audit_actor, "execution.state_changed", target_status,
                                     node_id=node_id, error_code=error_code, error_message=error_message,
                                     data={"from": current, "to": target_status})
        if target_status in self.TERMINAL_EXECUTION_STATES:
            await self.governance.audit(execution, audit_actor, f"workflow.execution.{target_status}",
                                        "success" if target_status == "completed" else target_status,
                                        error_code=error_code)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def cancel(self, execution: WorkflowExecution, actor_id: UUID, reason: str | None = None) -> WorkflowExecution:
        message = reason.strip() if reason and reason.strip() else "Workflow Execution cancelled by operator"
        return await self.transition(execution, "cancelled", error_code="EXECUTION_CANCELLED",
                                     error_message=message, actor_id=actor_id)

    async def retry(self, execution: WorkflowExecution, actor_id: UUID) -> WorkflowExecution:
        execution = await self._lock_execution(execution)
        if execution.status != "failed":
            raise HTTPException(409, "只有 failed Execution 可以 Retry")
        WorkflowRuntime.validate_definition((await self.db.execute(
            select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id)
        )).scalar_one().definition)
        retry_execution = WorkflowExecution(
            tenant_id=execution.tenant_id, workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id, created_by=actor_id,
            retry_of_execution_id=execution.id, status="pending", input_data=dict(execution.input_data or {}),
        )
        self.db.add(retry_execution)
        await self.db.flush()
        await self.governance.audit(execution, actor_id, "workflow.execution.retry_requested", "success")
        await self.governance.trace(execution, actor_id, "execution.retry_requested", execution.status,
                                     data={"retry_execution_id": str(retry_execution.id)})
        await self.governance.audit(retry_execution, actor_id, "workflow.execution.created", "success")
        await self.governance.trace(retry_execution, actor_id, "execution.created", "pending", data={
            "retry_of_execution_id": str(execution.id),
            "input_keys": sorted((execution.input_data or {}).keys()),
        })
        await self.db.commit()
        await self.db.refresh(retry_execution)
        return retry_execution

    async def transition_node(self, execution: WorkflowExecution, node_id: str, target_status: str,
                              input_data: dict | None = None, output_data: dict | None = None,
                              error_code: str | None = None, error_message: str | None = None) -> WorkflowNodeExecution:
        if target_status not in self.NODE_STATES:
            raise HTTPException(400, "不支持的 Node Execution 状态")
        execution = await self._lock_execution(execution)
        if execution.status in self.TERMINAL_EXECUTION_STATES:
            raise HTTPException(409, "已结束 Execution 不允许继续推进节点")
        node = (await self.db.execute(select(WorkflowNodeExecution).where(
            WorkflowNodeExecution.execution_id == execution.id, WorkflowNodeExecution.node_id == node_id
        ))).scalar_one_or_none()
        if node is None:
            node = WorkflowNodeExecution(execution_id=execution.id, node_id=node_id, attempt=1)
            self.db.add(node)
            await self.db.flush()
        allowed = {"pending": {"running", "skipped"}, "running": {"completed", "failed", "skipped"},
                   "completed": set(), "failed": {"running"}, "skipped": set()}
        if target_status not in allowed[node.status]:
            raise HTTPException(409, f"Node 不允许从 {node.status} 到 {target_status}")
        now = datetime.now(UTC).replace(tzinfo=None)
        previous_status = node.status
        if target_status == "running" and previous_status == "failed":
            if node.error_code == "CIRCUIT_OPEN":
                raise CircuitOpenError(f"node:{node_id}")
            node.attempt += 1
            node.ended_at = None
        node.status = target_status
        if input_data is not None:
            node.input_data = input_data
        if output_data is not None:
            node.output_data = output_data
        if error_code is not None:
            node.error_code = error_code
        if error_message is not None:
            node.error_message = error_message
        if target_status == "running":
            node.started_at = now
            execution.current_node_id = node_id
        if target_status in {"completed", "failed", "skipped"}:
            node.ended_at = now
        await self.governance.trace(execution, execution.created_by, "node.state_changed", target_status,
                                     node_id=node_id, error_code=error_code, error_message=error_message,
                                     data={"attempt": node.attempt})
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def run(self, execution: WorkflowExecution, version: WorkflowVersion, actor_id: UUID, admin: bool = False) -> WorkflowExecution:
        execution = await self._lock_execution(execution)
        if execution.status != "pending":
            raise HTTPException(409, "只有 pending Execution 可以 Run")
        await self.transition(execution, "running", actor_id=actor_id)
        runtime = WorkflowRuntime(self.db)
        try:
            await runtime.execute(execution, version, actor_id, admin)
        except CircuitOpenError:
            await self.transition(execution, "failed", error_code="CIRCUIT_OPEN", error_message="Circuit Breaker is open", actor_id=actor_id)
            raise HTTPException(503, "Circuit Breaker is open")
        except HTTPException as exc:
            if exc.status_code == 504:
                await self.transition(execution, "failed", error_code="WORKFLOW_TIMEOUT", error_message=str(exc.detail), actor_id=actor_id)
            elif exc.status_code >= 500:
                await self.transition(execution, "failed", error_code=f"HTTP_{exc.status_code}", error_message=str(exc.detail), actor_id=actor_id)
            else:
                await self.transition(execution, "failed", error_code=f"HTTP_{exc.status_code}", error_message=str(exc.detail), actor_id=actor_id)
            raise
        except Exception as exc:
            await self.transition(execution, "failed", error_code="RUNTIME_ERROR", error_message=str(exc), actor_id=actor_id)
            raise HTTPException(500, "Workflow Runtime 执行失败") from exc
        return await self._lock_execution(execution)
