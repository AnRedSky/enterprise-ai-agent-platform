"""Durable Frontier Runtime Entry Contract。

职责：为 Durable Frontier Worker 提供统一的 Execution Runtime 入口适配层。
边界：不实现新的 Node Runtime；复用 WorkflowRuntime、WorkflowExecutionService、Checkpoint
fencing 与现有 Worker resume preparation。Delegation Worker Execution 通过正式 Bridge
装配目标 Agent version、model profile、显式输入、context/tool refs 与 trace identity。
"""

from __future__ import annotations

import asyncio
from time import monotonic
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.runtime.workflow import CircuitOpenError
from app.services.agent_delegation.completion import complete_delegation, fail_delegation
from app.services.agent_delegation.runtime_bridge import AgentDelegationRuntimeBridge
from app.services.workflow import WorkflowExecutionService
from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_WORKER_FINISHED,
    RECOVERY_WORKER_STARTED,
    WorkflowRecoveryEvent,
)
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService
from app.services.workflow_worker.lease_guard import WorkflowWorkerLeaseGuard, WorkflowWorkerLeaseLost
from app.services.workflow_worker.resume_runtime import DurableResumeWorkflowRuntime


async def _finalize_delegation(execution_id: UUID, delegation_id: UUID, outcome: str, reason_code: str | None) -> None:
    """按 Worker generation 收敛 Delegation 终态。"""
    if outcome == "aborted":
        return
    async with SessionLocal() as db:
        execution = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
        ).scalar_one_or_none()
        if execution is None:
            raise HTTPException(409, "Worker Execution 不存在，无法收敛 Delegation")
        if outcome == "completed":
            await complete_delegation(
                db=db,
                tenant_id=execution.tenant_id,
                delegation_id=delegation_id,
                worker_execution_id=execution_id,
            )
            return
        await fail_delegation(
            db=db,
            tenant_id=execution.tenant_id,
            delegation_id=delegation_id,
            worker_execution_id=execution_id,
            error_code=reason_code or "RUNTIME_ERROR",
            error_message=execution.error_message or "Worker Execution 执行失败",
        )


async def execute_claimed_execution(worker, execution_id: UUID) -> None:
    """执行已 Claim 的 Execution；Delegation Worker 使用同一 WorkflowRuntime 执行目标 Agent。"""
    async with SessionLocal() as db:
        execution = (
            await db.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.worker_owner == worker.owner,
                    WorkflowExecution.status.in_({"pending", "running"}),
                )
            )
        ).scalar_one_or_none()
        if execution is None:
            return

        # SQLAlchemy AsyncSession 默认 expire_on_commit=True；WorkflowRuntime / lifecycle
        # 会在执行过程中提交事务，使 ORM instance 的属性在 finally 中可能变为 expired。
        # Worker generation 的 identity 是稳定的不可变输入，必须在任何 commit 前快照，
        # 后续 finalize、telemetry 与 fencing 均只使用这个 UUID，避免隐式 lazy-load。
        worker_execution_id = execution.id

        version = (
            await db.execute(select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id))
        ).scalar_one_or_none()
        workflow = (
            await db.execute(select(Workflow).where(Workflow.id == execution.workflow_id))
        ).scalar_one_or_none()
        if version is None or workflow is None:
            raise RuntimeError("Worker Execution 关联的 Workflow/Version 不存在")

        delegation_context = await AgentDelegationRuntimeBridge.load(db, execution)
        runtime_version = (
            AgentDelegationRuntimeBridge.build_runtime_version(version, delegation_context)
            if delegation_context is not None
            else version
        )
        allow_legacy_empty_nodes = "scheduled_slot" in (execution.input_data or {}) and delegation_context is None
        runtime_config = runtime_version.definition.get("config") if isinstance(runtime_version.definition, dict) else {}
        execution_timeout = DurableResumeWorkflowRuntime.resolve_timeout_ms(runtime_config or {}) / 1000 + worker.EXECUTION_TIMEOUT_GRACE_SECONDS
        service = WorkflowExecutionService(db)
        trace_link = WorkflowRecoveryTraceLinkService(db)
        recovery_trace_id = delegation_context.trace_id if delegation_context is not None else await trace_link.get_trace_id(execution)
        started = monotonic()
        outcome = "completed"
        reason_code = None

        if recovery_trace_id:
            worker.telemetry.emit(
                WorkflowRecoveryEvent(
                    event_name=RECOVERY_WORKER_STARTED,
                    execution_id=worker_execution_id,
                    resume_execution_id=worker_execution_id,
                    trace_id=recovery_trace_id,
                    phase="worker",
                )
            )

        if delegation_context is None:
            await worker._recover_orphaned_running_nodes(execution, service)
            execution, runtime_version = await worker._prepare_resume_runtime(db, execution, version)

        if execution.status == "pending":
            await service.transition(execution, "running", actor_id=execution.created_by)
        elif execution.status == "running":
            if execution.worker_owner != worker.owner:
                raise HTTPException(409, "Workflow Execution Worker ownership 已失效")
        else:
            return

        async def _run_runtime() -> object:
            runtime = DurableResumeWorkflowRuntime(db, execution_service=service)
            return await asyncio.wait_for(
                runtime.execute(
                    execution,
                    runtime_version,
                    execution.created_by,
                    allow_legacy_empty_nodes=allow_legacy_empty_nodes,
                ),
                timeout=execution_timeout,
            )

        renew_lease = getattr(worker, "_renew_with_abort_signal", None)
        if renew_lease is None:
            renew_lease = worker._renew_lease_once
        guard = WorkflowWorkerLeaseGuard(
            renew_lease=lambda: renew_lease(worker_execution_id),
            interval_seconds=max(0.1, worker.lease_seconds / 3),
        )
        try:
            await guard.run(_run_runtime())
        except WorkflowWorkerLeaseLost:
            outcome = "aborted"
            reason_code = "WORKER_LEASE_LOST"
            return
        except CircuitOpenError:
            outcome = "failed"
            reason_code = "CIRCUIT_OPEN"
            current = await service._lock_execution(execution)
            if current.status == "running":
                await service.transition(current, "failed", error_code=reason_code, error_message="Circuit Breaker is open", actor_id=current.created_by)
            raise HTTPException(503, "Circuit Breaker is open")
        except asyncio.TimeoutError as exc:
            outcome = "failed"
            reason_code = "WORKER_EXECUTION_TIMEOUT"
            current = await service._lock_execution(execution)
            if current.status == "running":
                await service.transition(current, "failed", error_code=reason_code, error_message="Worker Execution 超过受控执行时间", actor_id=current.created_by)
            raise RuntimeError("Worker Execution 超过受控执行时间") from exc
        except HTTPException as exc:
            outcome = "failed"
            reason_code = f"HTTP_{exc.status_code}"
            if exc.status_code == 504:
                detail = str(exc.detail)
                reason_code = "WORKFLOW_TIMEOUT" if detail in {
                    "Workflow deadline exceeded",
                    "Retry backoff exceeds workflow deadline",
                } else "NODE_TIMEOUT"
            current = await service._lock_execution(execution)
            if current.status == "running":
                await service.transition(current, "failed", error_code=reason_code, error_message=str(exc.detail), actor_id=current.created_by)
            raise
        except (ConnectionError, TimeoutError) as exc:
            outcome = "failed"
            reason_code = "CONNECTION_ERROR" if isinstance(exc, ConnectionError) else "NODE_TIMEOUT"
            current = await service._lock_execution(execution)
            if current.status == "running":
                await service.transition(current, "failed", error_code=reason_code, error_message=str(exc), actor_id=current.created_by)
            raise
        except Exception as exc:
            outcome = "failed"
            reason_code = "RUNTIME_ERROR"
            current = await service._lock_execution(execution)
            if current.status == "running":
                await service.transition(current, "failed", error_code=reason_code, error_message=str(exc), actor_id=current.created_by)
            raise HTTPException(500, "Workflow Runtime 执行失败") from exc
        finally:
            if delegation_context is not None:
                await _finalize_delegation(worker_execution_id, delegation_context.delegation_id, outcome, reason_code)
            if recovery_trace_id:
                worker.telemetry.emit(
                    WorkflowRecoveryEvent(
                        event_name=RECOVERY_WORKER_FINISHED,
                        execution_id=worker_execution_id,
                        resume_execution_id=worker_execution_id,
                        trace_id=recovery_trace_id,
                        outcome=outcome,
                        reason_code=reason_code,
                        phase="worker",
                        duration_ms=(monotonic() - started) * 1000,
                    )
                )
