"""Workflow Execution 领域服务。

职责：管理 Workflow Execution 与 Node Execution 状态机、幂等创建、重试、取消、Durable Resume 创建及 Runtime 执行入口。
边界：不负责 Workflow Registry 生命周期、不复制 Runtime 节点执行算法；节点执行统一委托 WorkflowRuntime。
关键依赖：Workflow/Execution ORM、WorkflowRuntime、WorkflowGovernanceService、Checkpoint Recovery 服务与 Workflow Runtime CircuitBreaker。
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
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution, WorkflowFrontier
from app.models.workflow_trace import WorkflowTraceEvent
from app.runtime.workflow import CircuitOpenError, WorkflowRuntime
from app.services.workflow.checkpoint import (
    WorkflowExecutionCheckpointRecoveryService,
    WorkflowExecutionCheckpointService,
)
from app.services.workflow.governance import WorkflowGovernanceService


class WorkflowExecutionService:
    """Workflow Execution 状态机、创建与 Durable Resume 持久化契约的领域服务。"""

    EXECUTION_STATES = {"pending", "running", "completed", "failed", "cancelled"}
    NODE_STATES = {"pending", "running", "completed", "failed", "skipped"}
    TERMINAL_EXECUTION_STATES = {"completed", "failed", "cancelled"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.governance = WorkflowGovernanceService(db)
        self.checkpoint = WorkflowExecutionCheckpointService(db)
        self.checkpoint_recovery = WorkflowExecutionCheckpointRecoveryService()

    async def create(self, workflow: Workflow, version: WorkflowVersion, actor_id: UUID, input_data: dict,
                     idempotency_key: str | None = None, *, commit: bool = True) -> WorkflowExecution:
        """创建 pending Execution，并由调用方选择是否立即提交事务。"""
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
        if commit:
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

    @staticmethod
    def _validate_execution_fencing(*, expected_worker_owner: str | None, expected_worker_attempt: int,
                                    locked_worker_owner: str | None, locked_worker_attempt: int) -> None:
        """校验 Execution ownership + fencing generation，阻断 stale Worker。"""
        if expected_worker_owner is None:
            return
        if locked_worker_owner != expected_worker_owner or locked_worker_attempt != expected_worker_attempt:
            raise HTTPException(409, "Workflow Execution Worker ownership 或 fencing generation 已失效")

    async def _lock_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """在状态转换前重新读取 Execution 行并加锁，同时阻断失去租约或 generation 失效的旧 Worker。"""
        if not isinstance(self.db, AsyncSession):
            return execution
        locked = (await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution.id).with_for_update()
        )).scalar_one_or_none()
        if locked is None:
            raise HTTPException(404, "Workflow Execution 不存在")
        self._validate_execution_fencing(
            expected_worker_owner=execution.worker_owner,
            expected_worker_attempt=int(execution.worker_attempt or 0),
            locked_worker_owner=locked.worker_owner,
            locked_worker_attempt=int(locked.worker_attempt or 0),
        )
        return locked

    async def _terminalize_owned_frontier_for_execution(self, execution: WorkflowExecution,
                                                        target_status: str, now: datetime) -> None:
        """在 Execution 终态事务内关闭当前 Worker 正在执行的唯一 Frontier。"""
        result = await self.db.execute(
            select(WorkflowFrontier)
            .where(
                WorkflowFrontier.tenant_id == execution.tenant_id,
                WorkflowFrontier.execution_id == execution.id,
                WorkflowFrontier.status.in_(("pending", "retry_wait", "claimed", "running")),
            )
            .with_for_update()
        )
        active_frontiers = list(result.scalars().all())
        if not active_frontiers:
            return
        if len(active_frontiers) != 1:
            raise HTTPException(409, "Execution 仍存在多个活动 Frontier，不允许直接进入 terminal 状态")
        frontier = active_frontiers[0]
        if frontier.status != "running":
            raise HTTPException(409, "Execution 仍存在尚未执行的 Frontier，不允许直接进入 terminal 状态")
        if frontier.worker_owner != execution.worker_owner:
            raise HTTPException(409, "Frontier Worker ownership 已失效")
        if int(frontier.attempt or 0) <= 0 or int(frontier.attempt or 0) != int(execution.worker_attempt or 0):
            raise HTTPException(409, "Frontier fencing generation 已失效")
        if frontier.worker_lease_expires_at is None or frontier.worker_lease_expires_at <= now:
            raise HTTPException(409, "Frontier Worker lease 已失效")
        frontier.status = target_status
        frontier.completed_at = now if target_status in {"completed", "failed"} else None
        frontier.worker_owner = None
        frontier.worker_lease_expires_at = None

    async def _assert_no_active_frontiers_for_terminal_transition(self, execution: WorkflowExecution, now: datetime,
                                                                  target_status: str) -> None:
        """终止 Execution 前验证 Frontier 生命周期，并原子关闭当前 Worker 的执行 Frontier。"""
        await self._terminalize_owned_frontier_for_execution(execution, target_status, now)

    def _validate_run_owner(self, execution: WorkflowExecution, worker_owner: str | None) -> None:
        """校验 Runtime 执行者是否与已认领 Execution 的 Worker owner 一致。"""
        claimed_owner = execution.worker_owner
        if claimed_owner is None:
            if worker_owner is not None:
                raise HTTPException(409, "Workflow Execution Worker ownership 已失效")
            return
        if worker_owner != claimed_owner:
            raise HTTPException(409, "只有 pending Execution 可以 Run")

    async def transition(self, execution: WorkflowExecution, target_status: str, node_id: str | None = None,
                         error_code: str | None = None, error_message: str | None = None,
                         output_data: dict | None = None, actor_id: UUID | None = None,
                         *, commit: bool = True) -> WorkflowExecution:
        """推进 Execution 状态，并允许调用方控制事务提交边界。"""
        if target_status not in self.EXECUTION_STATES:
            raise HTTPException(400, "不支持的 Execution 状态")
        execution = await self._lock_execution(execution)
        current = execution.status
        allowed = {"pending": {"running", "cancelled"}, "running": {"completed", "failed", "cancelled"},
                   "completed": set(), "failed": set(), "cancelled": set()}
        if target_status not in allowed[current]:
            raise HTTPException(409, f"Execution 不允许从 {current} 转换到 {target_status}")
        now = datetime.now(UTC).replace(tzinfo=None)
        if target_status in {"completed", "failed"}:
            await self._assert_no_active_frontiers_for_terminal_transition(execution, now, target_status)
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
            execution.worker_owner = None
            execution.worker_lease_expires_at = None
        audit_actor = actor_id or execution.created_by
        await self.governance.trace(execution, audit_actor, "execution.state_changed", target_status,
                                     node_id=node_id, error_code=error_code, error_message=error_message,
                                     data={"from": current, "to": target_status})
        if target_status in self.TERMINAL_EXECUTION_STATES:
            await self.governance.audit(execution, audit_actor, f"workflow.execution.{target_status}",
                                        "success" if target_status == "completed" else target_status,
                                        error_code=error_code)
        if commit:
            await self.db.commit()
            await self.db.refresh(execution)
        return execution

    async def cancel(self, execution: WorkflowExecution, actor_id: UUID, reason: str | None = None,
                     *, commit: bool = True) -> WorkflowExecution:
        """取消 Execution，并允许 Operator Governance 延迟提交。"""
        message = reason.strip() if reason and reason.strip() else "Workflow Execution cancelled by operator"
        return await self.transition(execution, "cancelled", error_code="EXECUTION_CANCELLED",
                                     error_message=message, actor_id=actor_id, commit=commit)

    async def retry(self, execution: WorkflowExecution, actor_id: UUID, *, commit: bool = True) -> WorkflowExecution:
        """为 failed Execution 创建 Retry Execution，并由调用方控制事务提交边界。"""
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
            "retry_of_execution_id": str(execution.id), "input_keys": sorted((execution.input_data or {}).keys()),
        })
        if commit:
            await self.db.commit()
            await self.db.refresh(retry_execution)
        return retry_execution

    async def resume_from_latest_checkpoint(self, execution: WorkflowExecution, actor_id: UUID,
                                            *, commit: bool = True) -> WorkflowExecution:
        """基于最新可恢复 Checkpoint 创建新的 pending Resume Execution，不启动 Runtime。"""
        execution = await self._lock_execution(execution)
        checkpoint = await self.checkpoint.latest(execution.id)
        assessment = self.checkpoint_recovery.assess(
            execution_id=execution.id,
            workflow_version_id=execution.workflow_version_id,
            execution_status=execution.status,
            worker_owner=execution.worker_owner,
            checkpoint=checkpoint,
        )
        if not assessment.eligible:
            raise HTTPException(409, f"Execution 不满足 Durable Resume 条件: {assessment.reason_code}")
        if assessment.resume_idempotency_key is None or assessment.checkpoint_sequence is None:
            raise HTTPException(409, "Resume Candidate 缺少确定性幂等键")
        version = (await self.db.execute(
            select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id)
        )).scalar_one_or_none()
        if version is None:
            raise HTTPException(409, "Workflow Execution 原始版本不存在")
        WorkflowRuntime.validate_definition(version.definition, allow_legacy_empty_nodes=True)
        existing = (await self.db.execute(select(WorkflowExecution).where(
            WorkflowExecution.tenant_id == execution.tenant_id,
            WorkflowExecution.idempotency_key == assessment.resume_idempotency_key,
        ))).scalar_one_or_none()
        if existing is not None:
            if existing.resume_of_execution_id != execution.id or existing.resume_checkpoint_sequence != assessment.checkpoint_sequence:
                raise HTTPException(409, "Resume 幂等键已绑定其他 Execution")
            return existing
        resume_execution = WorkflowExecution(
            tenant_id=execution.tenant_id, workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id, created_by=actor_id,
            resume_of_execution_id=execution.id, resume_checkpoint_sequence=assessment.checkpoint_sequence,
            idempotency_key=assessment.resume_idempotency_key, status="pending",
            input_data=dict(assessment.state_data or {}),
        )
        try:
            async with self.db.begin_nested():
                self.db.add(resume_execution)
                await self.db.flush()
        except IntegrityError:
            existing = (await self.db.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == execution.tenant_id,
                WorkflowExecution.idempotency_key == assessment.resume_idempotency_key,
            ))).scalar_one_or_none()
            if existing is None:
                raise
            if existing.resume_of_execution_id != execution.id or existing.resume_checkpoint_sequence != assessment.checkpoint_sequence:
                raise HTTPException(409, "Resume 幂等键已绑定其他 Execution")
            return existing
        await self.governance.audit(execution, actor_id, "workflow.execution.resume_requested", "success", metadata={
            "resume_execution_id": str(resume_execution.id), "checkpoint_id": str(assessment.checkpoint_id) if assessment.checkpoint_id else None,
            "checkpoint_sequence": assessment.checkpoint_sequence, "workflow_version_id": str(execution.workflow_version_id),
        })
        await self.governance.trace(execution, actor_id, "execution.resume_requested", execution.status, data={
            "resume_execution_id": str(resume_execution.id), "checkpoint_id": str(assessment.checkpoint_id) if assessment.checkpoint_id else None,
            "checkpoint_sequence": assessment.checkpoint_sequence,
        })
        await self.governance.audit(resume_execution, actor_id, "workflow.execution.created", "success", metadata={
            "creation_mode": "durable_resume", "resume_of_execution_id": str(execution.id),
            "resume_checkpoint_sequence": assessment.checkpoint_sequence,
        })
        await self.governance.trace(resume_execution, actor_id, "execution.created", "pending", data={
            "creation_mode": "durable_resume", "resume_of_execution_id": str(execution.id),
            "resume_checkpoint_sequence": assessment.checkpoint_sequence, "workflow_version_id": str(execution.workflow_version_id),
        })
        if commit:
            await self.db.commit()
            await self.db.refresh(resume_execution)
        return resume_execution

    async def transition_node(self, execution: WorkflowExecution, node_id: str, target_status: str,
                              input_data: dict | None = None, output_data: dict | None = None,
                              error_code: str | None = None, error_message: str | None = None,
                              *, commit: bool = True) -> WorkflowNodeExecution:
        """推进 Node Execution 状态，并在 Worker 场景执行 ownership fencing。"""
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
        is_retry = target_status == "running" and previous_status == "failed"
        if is_retry:
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
        if is_retry:
            await self.governance.trace(execution, execution.created_by, "node.retry.scheduled", "running",
                                        node_id=node_id, data={"attempt": node.attempt})
        await self.governance.trace(execution, execution.created_by, "node.state_changed", target_status,
                                    node_id=node_id, error_code=error_code, error_message=error_message,
                                    data={"attempt": node.attempt})
        if target_status == "completed":
            await self.checkpoint.append_next_in_transaction(
                execution_id=execution.id, execution_status=execution.status,
                state_data=dict(output_data if output_data is not None else (node.output_data or {})),
                checkpoint_reason="node.completed", node_id=node.node_id, node_attempt=node.attempt,
                node_status=node.status, input_data=node.input_data, output_data=node.output_data,
                worker_owner=execution.worker_owner, expected_worker_owner=execution.worker_owner,
                expected_worker_attempt=int(execution.worker_attempt or 0),
            )
        if commit:
            await self.db.commit()
            await self.db.refresh(node)
        return node

    async def run(self, execution: WorkflowExecution, version: WorkflowVersion, actor_id: UUID, admin: bool = False,
                  allow_legacy_empty_nodes: bool = False, worker_owner: str | None = None,
                  *, commit: bool = True) -> WorkflowExecution:
        """执行已发布 Workflow，并把统一事务提交边界传递给 WorkflowRuntime。"""
        execution = await self._lock_execution(execution)
        if execution.status != "pending":
            raise HTTPException(409, "只有 pending Execution 可以 Run")
        self._validate_run_owner(execution, worker_owner)
        await self.transition(execution, "running", actor_id=actor_id, commit=commit)
        runtime = WorkflowRuntime(self.db, execution_service=self)
        try:
            await runtime.execute(
                execution,
                version,
                actor_id,
                admin,
                allow_legacy_empty_nodes=allow_legacy_empty_nodes,
                commit=commit,
            )
        except CircuitOpenError:
            await self.transition(execution, "failed", error_code="CIRCUIT_OPEN", error_message="Circuit Breaker is open", actor_id=actor_id, commit=commit)
            raise HTTPException(503, "Circuit Breaker is open")
        except HTTPException as exc:
            if exc.status_code == 504:
                detail = str(exc.detail)
                timeout_code = "WORKFLOW_TIMEOUT" if detail in {"Workflow deadline exceeded", "Retry backoff exceeds workflow deadline"} else "NODE_TIMEOUT"
                await self.transition(execution, "failed", error_code=timeout_code, error_message=detail, actor_id=actor_id, commit=commit)
            else:
                await self.transition(execution, "failed", error_code=f"HTTP_{exc.status_code}", error_message=str(exc.detail), actor_id=actor_id, commit=commit)
            raise
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as exc:
            error_code = "CONNECTION_ERROR" if isinstance(exc, ConnectionError) else "NODE_TIMEOUT"
            await self.transition(execution, "failed", error_code=error_code, error_message=str(exc), actor_id=actor_id, commit=commit)
            raise
        except Exception as exc:
            await self.transition(execution, "failed", error_code="RUNTIME_ERROR", error_message=str(exc), actor_id=actor_id, commit=commit)
            raise HTTPException(500, "Workflow Runtime 执行失败") from exc
        if commit:
            return await self._lock_execution(execution)
        return execution
