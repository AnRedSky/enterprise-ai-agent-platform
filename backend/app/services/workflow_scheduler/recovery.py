"""Workflow Execution 自动恢复扫描器。

职责：Scheduler 侧按固定轮询发现 failed Execution，并把每个候选交给唯一 Recovery Domain Service。
边界：不复制 Recovery Policy、不创建 Resume Execution、不抢 Worker lease、不启动 Runtime；只负责“什么时候检查”。
关键依赖：SessionLocal、WorkflowExecution ORM、WorkflowExecutionAutomaticRecoveryService、Recovery Event Logger。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.checkpoint.recovery.automatic import WorkflowExecutionAutomaticRecoveryService
from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_SCAN_COMPLETED,
    WorkflowRecoveryEvent,
    WorkflowRecoveryEventLogger,
)
from app.services.workflow.checkpoint.recovery.policy import WorkflowExecutionRecoveryPolicy

logger = logging.getLogger(__name__)
event_logger = WorkflowRecoveryEventLogger(logger)


@dataclass(frozen=True)
class WorkflowRecoveryScanResult:
    """一次 Recovery Scan 的聚合计数。"""

    candidates: int = 0
    eligible: int = 0
    recovered: int = 0
    rejected: int = 0
    contention: int = 0
    failed: int = 0
    created: int = 0
    idempotency_hit: int = 0


class WorkflowRecoveryScheduler:
    """按轮询时间发现 failed Execution，并委托 Recovery Domain 执行自动恢复。"""

    DEFAULT_SCAN_LIMIT = 50
    MAX_SCAN_LIMIT = 500
    DEFAULT_POLL_INTERVAL_SECONDS = 5.0

    def __init__(
        self,
        scan_limit: int = DEFAULT_SCAN_LIMIT,
        policy: WorkflowExecutionRecoveryPolicy | None = None,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        if isinstance(scan_limit, bool) or not 1 <= scan_limit <= self.MAX_SCAN_LIMIT:
            raise ValueError(f"scan_limit 必须在 1-{self.MAX_SCAN_LIMIT} 范围内")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        self.scan_limit = scan_limit
        self.policy = policy or WorkflowExecutionRecoveryPolicy()
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    async def scan_once(self, now: datetime | None = None) -> WorkflowRecoveryScanResult:
        """执行一次全租户 Recovery Scan，并让 Domain 决定每个候选是否可恢复。"""
        current = now or datetime.now(UTC)
        async with SessionLocal() as discovery_db:
            query = (
                select(WorkflowExecution.id)
                .where(
                    WorkflowExecution.status == "failed",
                    WorkflowExecution.worker_owner.is_(None),
                )
                .order_by(WorkflowExecution.ended_at.asc().nulls_last(), WorkflowExecution.id.asc())
                .limit(self.scan_limit)
            )
            execution_ids = list((await discovery_db.execute(query)).scalars().all())

        counters = {
            "eligible": 0,
            "recovered": 0,
            "rejected": 0,
            "contention": 0,
            "failed": 0,
            "created": 0,
            "idempotency_hit": 0,
        }
        for execution_id in execution_ids:
            try:
                async with SessionLocal() as db:
                    execution = (
                        await db.execute(
                            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
                        )
                    ).scalar_one_or_none()
                    if execution is None:
                        counters["rejected"] += 1
                        continue

                    service = WorkflowExecutionAutomaticRecoveryService(db, self.policy)
                    recovery = await service.recover(execution, now=current)
                    if recovery.decision.eligible:
                        counters["eligible"] += 1
                    else:
                        counters["rejected"] += 1
                        continue

                    if recovery.outcome == "created":
                        counters["created"] += 1
                        counters["recovered"] += 1
                    elif recovery.outcome == "idempotency_hit":
                        counters["idempotency_hit"] += 1
                        counters["contention"] += 1
                        counters["recovered"] += 1
                    else:
                        counters["rejected"] += 1
            except Exception as exc:
                counters["failed"] += 1
                logger.exception(
                    "Workflow automatic recovery scan failed",
                    extra={"execution_id": str(execution_id), "error_type": type(exc).__name__},
                )

        result = WorkflowRecoveryScanResult(candidates=len(execution_ids), **counters)
        event_logger.emit(
            WorkflowRecoveryEvent(
                event_name=RECOVERY_SCAN_COMPLETED,
                candidates=result.candidates,
                eligible=result.eligible,
                recovered=result.recovered,
                rejected=result.rejected,
                contention=result.contention,
                failed=result.failed,
                scan_limit=self.scan_limit,
                occurred_at=current,
            )
        )
        return result

    async def run_forever(self) -> None:
        """持续执行 Recovery Scan，直到收到 stop 请求。"""
        self._stop_event.clear()
        while not self._stop_event.is_set():
            try:
                await self.scan_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Workflow automatic recovery scan loop failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """请求 Recovery Scan 循环停止。"""
        self._stop_event.set()
