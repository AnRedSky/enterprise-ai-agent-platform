"""Workflow Worker 领域服务。

职责：从 PostgreSQL 认领 pending Workflow Execution，并复用唯一 WorkflowExecutionService 执行 Runtime。
边界：不负责 Scheduled Trigger 时间计算、slot、misfire 或 Trigger API；Scheduler 只负责产生 pending Execution。
关键外部依赖：PostgreSQL、WorkflowExecutionService、Workflow/WorkflowVersion ORM。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.services.workflow import WorkflowExecutionService

logger = logging.getLogger(__name__)


class WorkflowWorker:
    """独立 Worker Service 的 PostgreSQL Execution 消费器。"""

    DEFAULT_POLL_INTERVAL_SECONDS = 0.2
    DEFAULT_CONCURRENCY = 8
    DEFAULT_LEASE_SECONDS = 60

    def __init__(
        self,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        concurrency: int = DEFAULT_CONCURRENCY,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
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

    async def execute_claimed(self, execution_id) -> None:
        """执行已认领的 Workflow Execution。"""
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
            version = (
                await db.execute(
                    select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id)
                )
            ).scalar_one_or_none()
            workflow = (
                await db.execute(select(Workflow).where(Workflow.id == execution.workflow_id))
            ).scalar_one_or_none()
            if version is None or workflow is None:
                raise RuntimeError("Worker Execution 关联的 Workflow/Version 不存在")
            allow_legacy_empty_nodes = "scheduled_slot" in (execution.input_data or {})
            try:
                await WorkflowExecutionService(db).run(
                    execution,
                    version,
                    execution.created_by,
                    allow_legacy_empty_nodes=allow_legacy_empty_nodes,
                )
            finally:
                current = (
                    await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution.id))
                ).scalar_one_or_none()
                if current is not None and current.status in {"completed", "failed", "cancelled"}:
                    current.worker_owner = None
                    current.worker_lease_expires_at = None
                    await db.commit()

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

    async def _run_with_guard(self, execution_id) -> None:
        """隔离单个任务异常，避免单个 Workflow 失败停止整个 Worker。"""
        async with self._semaphore:
            try:
                await self.execute_claimed(execution_id)
            except asyncio.CancelledError:
                raise
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
