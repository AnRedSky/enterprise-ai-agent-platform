"""Workflow Execution 自动恢复扫描器。

职责：Scheduler 侧按固定轮询发现 failed Execution，并把每个候选交给唯一 Recovery Domain Service。
边界：不复制 Recovery Policy、不创建 Resume Execution、不抢 Worker lease、不启动 Runtime；只负责“什么时候检查”。
关键依赖：SessionLocal、WorkflowExecution ORM、WorkflowExecutionAutomaticRecoveryService。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.checkpoint.recovery.automatic import (
    WorkflowExecutionAutomaticRecoveryService,
)
from app.services.workflow.checkpoint.recovery.policy import WorkflowExecutionRecoveryPolicy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowRecoveryScanResult:
    """一次 Recovery Scan 的聚合计数。"""

    candidates: int = 0
    eligible: int = 0
    recovered: int = 0
    rejected: int = 0
    contention: int = 0
    failed: int = 0


class WorkflowRecoveryScheduler:
    """按轮询时间发现 failed Execution，并委托 Recovery Domain 执行自动恢复。"""

    DEFAULT_SCAN_LIMIT = 50
    MAX_SCAN_LIMIT = 500

    def __init__(
        self,
        scan_limit: int = DEFAULT_SCAN_LIMIT,
        policy: WorkflowExecutionRecoveryPolicy | None = None,
    ):
        if isinstance(scan_limit, bool) or not 1 <= scan_limit <= self.MAX_SCAN_LIMIT:
            raise ValueError(f"scan_limit 必须在 1-{self.MAX_SCAN_LIMIT} 范围内")
        self.scan_limit = scan_limit
        self.policy = policy or WorkflowExecutionRecoveryPolicy()

    async def scan_once(self, now: datetime | None = None) -> WorkflowRecoveryScanResult:
        """执行一次全租户 Recovery Scan，并让 Domain 决定每个候选是否可恢复。

        Args:
            now: 可选当前时间，用于确定性测试和统一本轮策略判断。

        Returns:
            本轮发现、符合条件、恢复成功、策略拒绝、并发竞争和异常数量。

        事务边界：发现查询只读；每个 Execution 使用独立数据库 Session，避免 Scheduler 在跨候选循环中
        持有长事务。实际 Resume 创建由 Recovery Domain 与 WorkflowExecutionService 自己提交。

        并发边界：多个 Scheduler 实例可能同时发现同一个 failed Execution。最终 Resume 创建仍由
        Source Execution 行锁、确定性 idempotency key 与数据库唯一约束收敛；Scanner 本身不假设单实例。
        """
        current = now or datetime.now(UTC)
        result = WorkflowRecoveryScanResult()
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

        candidates = len(execution_ids)
        counters = {
            "eligible": 0,
            "recovered": 0,
            "rejected": 0,
            "contention": 0,
            "failed": 0,
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
                    evaluation = await service.evaluate(execution, now=current)
                    if not evaluation.decision.eligible:
                        counters["rejected"] += 1
                        continue
                    counters["eligible"] += 1
                    recovered = await service.recover(execution, now=current)
                    if recovered.resume_execution_id is not None:
                        counters["recovered"] += 1
                    else:
                        counters["rejected"] += 1
            except Exception as exc:
                counters["failed"] += 1
                logger.exception(
                    "Workflow automatic recovery scan failed",
                    extra={"execution_id": str(execution_id), "error_type": type(exc).__name__},
                )

        return WorkflowRecoveryScanResult(candidates=candidates, **counters)
