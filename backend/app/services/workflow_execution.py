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
        if idempotency_key:
            existing = (await self.db.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == workflow.tenant_id,
                WorkflowExecution.idempotency_key == idempotency_key,
            ))).scalar_one_or_none()
            if existing is not None:
                if existing.workflow_id != workflow.id or existing.workflow_version_id != version.id:
                    raise HTTPException(409, "Idempotency-Key 已用于其他 Workflow Execution")
                return existing
        execution = WorkflowExecution(
            tenant_id=workflow.tenant_id,
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            created_by=actor_id,
            idempotency_key=idempotency_key,
            status="pending",
            input_data=input_data,
        )
        self.db.add(execution)
        try:
            await self.db.flush()
        except IntegrityError:
            if not idempotency_key:
                raise
            await self.db.rollback()
            existing = (await self.db.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == workflow.tenant_id,
                WorkflowExecution.idempotency_key == idempotency_key,
            ))).scalar_one_or_none()
            if existing is None:
                raise
            if existing.workflow_id != workflow.id or existing.workflow_version_id != version.id:
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
                                     data={"from": previous_status, "to": target_status,
                                           "attempt": node.attempt,
                                           "input_present": input_data is not None,
                                           "output_present": output_data is not None})
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def run(self, execution: WorkflowExecution, version: WorkflowVersion, actor_id: UUID,
                  is_admin: bool = False) -> WorkflowExecution:
        definition = version.definition
        nodes = WorkflowRuntime.validate_definition(definition)
        runtime_config = definition.get("config") or {}
        retry_budget_config = runtime_config.get("retry_budget") or {}
        if not isinstance(retry_budget_config, dict):
            raise HTTPException(422, "retry_budget config 必须为对象")
        retry_budget_remaining = retry_budget_config.get("max_retries", 20)
        if isinstance(retry_budget_remaining, bool) or not isinstance(retry_budget_remaining, int) or not 0 <= retry_budget_remaining <= 100:
            raise HTTPException(422, "retry_budget.max_retries 必须在 0-100 范围内")
        workflow_timeout_ms = WorkflowRuntime.resolve_timeout_ms(runtime_config)
        execution = await self._lock_execution(execution)
        if execution.status != "pending":
            raise HTTPException(409, "只有 pending Execution 可以启动 Runtime")
        runtime = WorkflowRuntime(self.db)
        data = dict(execution.input_data or {})
        deadline = asyncio.get_running_loop().time() + workflow_timeout_ms / 1000
        await self.governance.audit(execution, actor_id, "workflow.execution.run", "started")
        try:
            await self.transition(execution, "running", actor_id=actor_id)
            for node in nodes:
                node_id = node["id"]
                node_timeout_ms = WorkflowRuntime.resolve_timeout_ms(node["config"])
                retry_policy = WorkflowRuntime.resolve_retry_policy(node["config"])
                node_execution = await self.transition_node(execution, node_id, "running", input_data=data)
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        await self.transition_node(execution, node_id, "failed", error_code="WORKFLOW_TIMEOUT",
                                                   error_message="Workflow Execution timeout")
                        await self.transition(execution, "failed", error_code="WORKFLOW_TIMEOUT",
                                              error_message="Workflow Execution timeout", actor_id=actor_id)
                        raise HTTPException(504, "Workflow Execution timeout")
                    effective_timeout = min(node_timeout_ms / 1000, remaining)
                    exc: BaseException | None = None
                    # Classify based on the configured node deadline versus the remaining workflow budget.
                    # Using effective_timeout >= remaining is incorrect because min() makes them equal whenever
                    # the workflow deadline wins, and event-loop overhead can make a 1ms node timeout appear
                    # to consume the workflow deadline after the loop has already elapsed several milliseconds.
                    workflow_timeout = remaining <= node_timeout_ms / 1000
                    try:
                        data = await asyncio.wait_for(
                            runtime.execute_node(node, data, actor_id, is_admin, execution.id, execution.tenant_id),
                            timeout=effective_timeout,
                        )
                    except asyncio.TimeoutError as caught:
                        exc = caught
                        error_code = WorkflowRuntime.classify_error(caught, workflow_timeout=workflow_timeout)
                        error_message = "Workflow Execution timeout" if workflow_timeout else f"Workflow node timeout: {node_id}"
                    except Exception as caught:
                        exc = caught
                        error_code = WorkflowRuntime.classify_error(caught)
                        error_message = str(caught) or "Workflow node execution failed"
                    else:
                        await self.transition_node(execution, node_id, "completed", output_data=data)
                        break

                    failed_node_execution = await self.transition_node(execution, node_id, "failed", error_code=error_code,
                                                                       error_message=error_message)
                    raw_attempt = getattr(failed_node_execution, "attempt", None)
                    if not isinstance(raw_attempt, int) or isinstance(raw_attempt, bool):
                        raw_attempt = getattr(node_execution, "attempt", 1)
                    attempt = raw_attempt if isinstance(raw_attempt, int) and not isinstance(raw_attempt, bool) else 1
                    retryable = error_code in retry_policy["retryable_error_codes"] and error_code not in {"WORKFLOW_TIMEOUT", "CIRCUIT_OPEN"}
                    can_retry = retryable and attempt < retry_policy["max_attempts"]
                    if not can_retry:
                        if retryable and attempt >= retry_policy["max_attempts"]:
                            await self.governance.audit(execution, actor_id, "workflow.node.retry_exhausted", "failed",
                                                        error_code=error_code)
                            await self.governance.trace(execution, actor_id, "node.retry.exhausted", "failed",
                                                        node_id=node_id, error_code=error_code,
                                                        error_message="Node retry max attempts exhausted",
                                                        data={"reason": "max_attempts", "attempt": attempt,
                                                              "max_attempts": retry_policy["max_attempts"]})
                        await self.transition(execution, "failed", error_code=error_code,
                                              error_message=error_message, actor_id=actor_id)
                        if error_code.startswith("HTTP_") and error_code in {"HTTP_429", "HTTP_502", "HTTP_503", "HTTP_504"}:
                            raise HTTPException(int(error_code.split("_", 1)[1]), error_message) from exc
                        if error_code == "NODE_TIMEOUT":
                            raise HTTPException(504, error_message) from exc
                        if error_code == "WORKFLOW_TIMEOUT":
                            raise HTTPException(504, error_message) from exc
                        if isinstance(exc, HTTPException):
                            raise exc
                        raise exc

                    if retry_budget_remaining <= 0:
                        await self.governance.audit(execution, actor_id, "workflow.node.retry_exhausted", "failed",
                                                    error_code=error_code)
                        await self.governance.trace(execution, actor_id, "node.retry.exhausted", "failed",
                                                    node_id=node_id, error_code=error_code,
                                                    error_message="Workflow retry budget exhausted",
                                                    data={"reason": "retry_budget", "attempt": attempt,
                                                          "max_attempts": retry_policy["max_attempts"],
                                                          "retry_budget_max": retry_budget_config.get("max_retries", 20)})
                        await self.transition(execution, "failed", error_code=error_code,
                                              error_message=error_message, actor_id=actor_id)
                        if error_code.startswith("HTTP_") and error_code in {"HTTP_429", "HTTP_502", "HTTP_503", "HTTP_504"}:
                            raise HTTPException(int(error_code.split("_", 1)[1]), error_message) from exc
                        if error_code == "NODE_TIMEOUT":
                            raise HTTPException(504, error_message) from exc
                        if isinstance(exc, HTTPException):
                            raise exc
                        raise exc

                    retry_budget_remaining -= 1
                    retry_delay = WorkflowRuntime.retry_delay_seconds(retry_policy, attempt, random.random())
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0 or retry_delay >= remaining:
                        await self.governance.audit(execution, actor_id, "workflow.node.retry_exhausted", "failed",
                                                    error_code="WORKFLOW_TIMEOUT")
                        await self.governance.trace(execution, actor_id, "node.retry.exhausted", "failed",
                                                    node_id=node_id, error_code="WORKFLOW_TIMEOUT",
                                                    error_message="Workflow retry budget consumed by deadline",
                                                    data={"reason": "workflow_deadline", "attempt": attempt,
                                                          "retry_delay_ms": int(retry_delay * 1000),
                                                          "retry_budget_remaining": retry_budget_remaining})
                        await self.transition(execution, "failed", error_code="WORKFLOW_TIMEOUT",
                                              error_message="Workflow Execution timeout", actor_id=actor_id)
                        raise HTTPException(504, "Workflow Execution timeout")
                    await self.governance.audit(execution, actor_id, "workflow.node.retry", "success",
                                                error_code=error_code)
                    await self.governance.audit(execution, actor_id, "workflow.node.retry_scheduled", "success",
                                                error_code=error_code)
                    await self.governance.trace(execution, actor_id, "node.retry.scheduled", "running",
                                                node_id=node_id, data={"attempt": attempt + 1,
                                                                       "delay_ms": int(retry_delay * 1000),
                                                                       "retry_budget_remaining": retry_budget_remaining})
                    if retry_delay > 0:
                        await asyncio.sleep(retry_delay)
                    node_execution = await self.transition_node(execution, node_id, "running", input_data=data)
        except HTTPException:
            raise
        except Exception as exc:
            if execution.status not in self.TERMINAL_EXECUTION_STATES:
                await self.transition(execution, "failed", error_code=WorkflowRuntime.classify_error(exc),
                                      error_message=str(exc) or "Workflow execution failed", actor_id=actor_id)
                raise HTTPException(500, str(exc) or "Workflow execution failed") from exc
            raise
        await self.transition(execution, "completed", output_data=data, actor_id=actor_id)
        return execution
