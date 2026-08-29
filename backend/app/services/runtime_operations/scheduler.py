"""Runtime 告警周期调度服务。

职责：在独立 Scheduler Service 中周期执行 Runtime Metrics 快照与 Alert Rule 评估。
边界：不启动 HTTP 服务、不直接执行通知网络请求；指标仍来自 Durable facts，告警转换由 RuntimeAlertEvaluator 进入 Integration Event。
关键依赖：SessionLocal、RuntimeOperationsEnterpriseService、RuntimeAlertEvaluator。
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.runtime_operations import RuntimeAlertRule
from app.services.runtime_operations import RuntimeOperationsEnterpriseService
from app.services.runtime_operations.alerting import RuntimeAlertEvaluator

logger = logging.getLogger(__name__)


class RuntimeAlertScheduler:
    """以租户为隔离边界执行 Runtime 指标快照和告警评估。"""

    def __init__(self, poll_interval_seconds: float = 60.0):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    async def tick_once(self) -> dict[str, int]:
        """执行一轮所有启用告警规则租户的指标采样与告警评估。

        Args:
            无。租户范围从 PostgreSQL 中当前启用的告警规则自动发现。

        Returns:
            包含 discovered、sampled 和 transitions 数量的本轮结果。

        设计意图：Scheduler 只负责周期编排；每个租户使用独立 Session，避免一个租户的事务或异常影响其他租户。
        """
        async with SessionLocal() as discovery_db:
            result = await discovery_db.execute(
                select(RuntimeAlertRule.tenant_id)
                .where(RuntimeAlertRule.enabled.is_(True))
                .distinct()
            )
            tenant_ids = list(result.scalars().all())

        sampled = 0
        transitions = 0
        for tenant_id in tenant_ids:
            async with SessionLocal() as db:
                try:
                    sampled += await RuntimeOperationsEnterpriseService(db).snapshot(tenant_id, window_hours=24)
                    changed = await RuntimeAlertEvaluator(db).evaluate(tenant_id, actor="scheduler")
                    transitions += len(changed)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("Runtime alert evaluation failed for tenant %s", tenant_id)
                    raise
        return {"discovered": len(tenant_ids), "sampled": sampled, "transitions": transitions}

    async def run_forever(self) -> None:
        """持续执行 Runtime 指标与告警周期任务，直到收到停止信号。"""
        while not self._stop_event.is_set():
            await self.tick_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """请求停止周期任务。"""
        self._stop_event.set()
