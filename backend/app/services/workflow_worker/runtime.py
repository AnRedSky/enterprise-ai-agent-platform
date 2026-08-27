"""Workflow Worker 领域服务。

职责：从 PostgreSQL 认领 pending Workflow Execution，并复用唯一 WorkflowExecutionService 执行 Runtime。
边界：不负责 Scheduled Trigger 时间计算、slot、misfire 或 Trigger API；Scheduler 只负责产生 pending Execution。
关键外部依赖：PostgreSQL、WorkflowExecutionService、Workflow/WorkflowVersion ORM、Recovery Trace Lineage。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, update

from app.infrastructure.db import SessionLocal
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.runtime.workflow import WorkflowRuntime
from app.services.workflow import WorkflowExecutionService
from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_WORKER_FINISHED,
    RECOVERY_WORKER_STARTED,
    WorkflowRecoveryEvent,
    WorkflowRecoveryEventLogger,
    WorkflowRecoveryTelemetry,
)
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService

logger = logging.getLogger(__name__)


class WorkflowWorker:
    """独立 Worker Service 的 PostgreSQL Execution 消费器。"""

    DEFAULT_POLL_INTERVAL_SECONDS = 0.2
    DEFAULT_CONCURRENCY = 8
    DEFAULT_LEASE_SECONDS = 60
    EXECUTION_TIMEOUT_GRACE_SECONDS = 5

    def __init__(
        self,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        concurrency: int = DEFAULT_CONCURRENCY,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        telemetry: WorkflowRecoveryTelemetry | None = None,
    ):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        if isinstance(concurrency, bool) or concurrency < 1:
            raise ValueError("concurrency 必须大于 0")
        if isinstance(lease_seconds, bool) or lease_seconds < 1:
            raise ValueError("lease_seconds 必须大于 0")
        self.poll_interval_seconds = poll_interval_seconds
        self.concurrency = concurrency
        self.lease_seconds = lease_seconds
        self.owner = f"worker:{uuid4()}"
        self._stop_event = asyncio.Event()
        self._semaphore = asyncio.Semaphore(concurrency)
        self.event_logger = WorkflowRecoveryEventLogger(logging.getLogger(__name__))
        self.telemetry = telemetry or WorkflowRecoveryTelemetry(event_logger=self.event_logger)

    async def claim_one(self, now: datetime | None = None) -> WorkflowExecution | None:
        """原子认领一个 pending Execution。"""
        now = now or datetime.now(UTC)
        now_naive = now.replace(tzinfo=None)
        lease_expires_at = now_naive + timedelta(seconds=self.lease_seconds)
        async with SessionLocal() as db:
            result = await db.execute(
                select(WorkflowExecution)
                .where(
                    WorkflowExecution.status == "pending",
                    (WorkflowExecution.worker_owner.is_(None))
                    | (WorkflowExecution.worker_lease_expires_at <= now_naive),
                )
                .order_by(WorkflowExecution.created_at.asc(), WorkflowExecution.id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            execution = result.scalar_one_or_none()
            if execution is None:
                await db.rollback()
                return None
            execution.worker_owner = self.owner
            execution.worker_lease_expires_at = lease_expires_at
            execution.worker_attempt = int(execution.worker_attempt or 0) + 1
            await db.commit()
            return execution

    async def _renew_lease_once(self, execution_id: UUID) -> bool:
        """原子刷新当前 Worker 的 Execution 租约。"""
        now = datetime.now(UTC).replace(tzinfo=None)
        lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        async with SessionLocal() as db:
            result = await db.execute(
                update(WorkflowExecution)
                .where(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.worker_owner == self.owner,
                    WorkflowExecution.status.in_({"pending", "running"}),
                    WorkflowExecution.worker_lease_expires_at > now,
                )
                .values(worker_lease_expires_at=lease_expires_at)
            )
            if result.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()
            return True

    async def _renew_lease_forever(self, execution_id: UUID) -> None:
        """持续刷新当前 Worker 的 Execution 租约。"""
        interval = max(0.1, self.lease_seconds / 3)
        while True:
            try:
                owned = await self._renew_lease_once(execution_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Workflow Worker lease heartbeat failed; will retry",
                    extra={"execution_id": str(execution_id), "worker_owner": self.owner},
                )
                owned = True
            if not owned:
                return
            await asyncio.sleep(interval)

    async def _recover_orphaned_running_nodes(self, execution: WorkflowExecution, service: WorkflowExecutionService) -> int:
        """在 Worker 接管 pending Execution 时收敛遗留的 running Node。"""
        result = await service.db.execute(
            select(WorkflowNodeExecution).where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowNodeExecution.status == "running",
            )
        )
        orphaned_nodes = list(result.scalars().all())
        for node in orphaned_nodes:
            await service.transition_node(
                execution,
                node.node_id,
                "failed",
                error_code="WORKER_RECOVERY_INTERRUPTED",
                error_message="Worker 接管 pending Execution 时发现遗留 running Node，已进入恢复态",
            )
        if orphaned_nodes:
            logger.warning(
                "Workflow Worker recovered orphaned running nodes",
                extra={
                    "execution_id": str(execution.id),
                    "worker_owner": self.owner,
                    "node_ids": [node.node_id for node in orphaned_nodes],
                },
            )
        return len(orphaned_nodes)

    async def _prepare_resume_runtime(self, db, execution: WorkflowExecution, version: WorkflowVersion) -> tuple[WorkflowExecution, object]:
        """根据 Resume Execution 的来源 Checkpoint 准备 Runtime 输入状态。"""
        if execution.resume_of_execution_id is None:
            return execution, version
        source_result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution.resume_of_execution_id,
                WorkflowExecution.tenant_id == execution.tenant_id,
            )
        )
        source = source_result.scalar_one_or_none()
        if source is None:
            raise RuntimeError("Resume 来源 Execution 不存在")
        if source.status != "failed" or source.worker_owner is not None:
            raise RuntimeError("Resume 来源 Execution 已不满足恢复安全边界")
        from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
        if execution.resume_checkpoint_sequence is None:
            raise RuntimeError("Resume Execution 缺少 checkpoint sequence")
        checkpoint_result = await db.execute(
            select(WorkflowExecutionCheckpoint).where(
                WorkflowExecutionCheckpoint.execution_id == source.id,
                WorkflowExecutionCheckpoint.sequence == execution.resume_checkpoint_sequence,
            )
        )
        checkpoint = checkpoint_result.scalar_one_or_none()
        if checkpoint is None:
            raise RuntimeError("Resume 来源 Checkpoint 不存在")
        if checkpoint.checkpoint_reason != "node.completed" or checkpoint.node_status != "completed":
            raise RuntimeError("Resume Checkpoint 不是合法的 Node completed 边界")
        if checkpoint.execution_status != "running" or checkpoint.node_id is None:
            raise RuntimeError("Resume Checkpoint Execution/Node 状态边界无效")
        if source.workflow_version_id != execution.workflow_version_id:
            raise RuntimeError("Resume 不允许发生 Workflow Version 漂移")
        execution.input_data = dict(checkpoint.state_data or {})
        return execution, version

    async def execute_claimed(self, execution_id: UUID) -> None:
        """执行已认领的 Workflow Execution，并限制单次 Runtime 执行时间。"""
        async with SessionLocal() as db:
            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == execution_id,
                        WorkflowExecution.worker_owner == self.owner,
                        WorkflowExecution.status == "pending",
                    )
                )
            ).scalar_one_or_none()
            if execution is None:
                return
            version = (await db.execute(select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id))).scalar_one_or_none()
            workflow = (await db.execute(select(Workflow).where(Workflow.id == execution.workflow_id))).scalar_one_or_none()
            if version is None or workflow is None:
                raise RuntimeError("Worker Execution 关联的 Workflow/Version 不存在")
            allow_legacy_empty_nodes = "scheduled_slot" in (execution.input_data or {})
            runtime_config = version.definition.get("config") if isinstance(version.definition, dict) else {}
            workflow_timeout_ms = WorkflowRuntime.resolve_timeout_ms(runtime_config or {})
            execution_timeout = workflow_timeout_ms / 1000 + self.EXECUTION_TIMEOUT_GRACE_SECONDS
            service = WorkflowExecutionService(db)
            trace_link = WorkflowRecoveryTraceLinkService(db)
            recovery_trace_id = await trace_link.get_trace_id(execution)
            started = monotonic()
            if recovery_trace_id:
                self.telemetry.emit(
                    WorkflowRecoveryEvent(
                        event_name=RECOVERY_WORKER_STARTED,
                        execution_id=execution.id,
                        resume_execution_id=execution.id,
                        trace_id=recovery_trace_id,
                        phase="worker",
                    )
                )
            await self._recover_orphaned_running_nodes(execution, service)
            execution, runtime_version = await self._prepare_resume_runtime(db, execution, version)
            lease_task = asyncio.create_task(self._renew_lease_forever(execution.id))
            outcome = "completed"
            reason_code = None
            try:
                await asyncio.wait_for(
                    service.run(
                        execution,
                        runtime_version,
                        execution.created_by,
                        allow_legacy_empty_nodes=allow_legacy_empty_nodes,
                        worker_owner=self.owner,
                    ),
                    timeout=execution_timeout,
                )
            except asyncio.TimeoutError as exc:
                outcome = "failed"
                reason_code = "WORKER_EXECUTION_TIMEOUT"
                current = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution.id))).scalar_one_or_none()
                if current is not None and current.status == "running":
                    try:
                        await service.transition(current, "failed", error_code=reason_code, error_message="Worker Execution 超过受控执行时间", actor_id=current.created_by)
                    except HTTPException:
                        await db.rollback()
                raise RuntimeError("Worker Execution 超过受控执行时间") from exc
            except Exception:
                outcome = "failed"
                reason_code = "WORKER_EXECUTION_FAILED"
                raise
            finally:
                lease_task.cancel()
                try:
                    await lease_task
                except asyncio.CancelledError:
                    pass
                current = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution.id))).scalar_one_or_none()
                if current is not None and current.status in {"completed", "failed", "cancelled"}:
                    current.worker_owner = None
                    current.worker_lease_expires_at = None
                    await db.commit()
                if recovery_trace_id:
                    self.telemetry.emit(
                        WorkflowRecoveryEvent(
                            event_name=RECOVERY_WORKER_FINISHED,
                            execution_id=execution.id,
                            resume_execution_id=execution.id,
                            trace_id=recovery_trace_id,
                            outcome=outcome,
                            reason_code=reason_code,
                            phase="worker",
                            duration_ms=(monotonic() - started) * 1000,
                        )
                    )

    async def dispatch_once(self) -> int:
        """批量认领并并发执行当前可用任务。"""
        tasks: list[asyncio.Task[None]] = []
        for _ in range(self.concurrency):
            execution = await self.claim_one()
            if execution is None:
                break
            tasks.append(asyncio.create_task(self._run_with_guard(execution.id)))
        if tasks:
            await asyncio.gather(*tasks)
        return len(tasks)

    async def _run_with_guard(self, execution_id: UUID) -> None:
        """隔离单个任务异常，并将失去租约的旧消费者视为正常竞争结果。"""
        async with self._semaphore:
            try:
                await self.execute_claimed(execution_id)
            except asyncio.CancelledError:
                raise
            except HTTPException as exc:
                if exc.status_code == 409 and exc.detail == "Workflow Execution Worker ownership 已失效":
                    logger.warning("Workflow Worker lost execution ownership; abandoning stale consumer", extra={"execution_id": str(execution_id), "worker_owner": self.owner})
                    return
                logger.exception("Workflow Worker execution failed", extra={"execution_id": str(execution_id), "status_code": exc.status_code})
            except Exception:
                logger.exception("Workflow Worker execution failed", extra={"execution_id": str(execution_id)})

    async def run_forever(self) -> None:
        """持续消费 PostgreSQL pending Execution，直到收到 stop()。"""
        self._stop_event.clear()
        while not self._stop_event.is_set():
            try:
                claimed = await self.dispatch_once()
                if claimed:
                    continue
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Workflow Worker polling failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """请求 Worker 主循环停止。"""
        self._stop_event.set()
