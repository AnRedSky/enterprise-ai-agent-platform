"""Runtime Alert 周期调度。

职责：周期发现启用 Runtime Alert Rule 的租户，并执行确定性的
Metric Sample -> Alert firing/recovery 评估。告警转换由 RuntimeAlertEvaluator
负责持久化 Audit 与 Durable Integration Event；通知路由和网络 Delivery
继续由 RuntimeNotificationScheduler / WebhookDeliveryWorker 负责。

边界：不执行外部网络调用，不绕过 Alert Evaluator 修改告警事实；每个 tenant
使用独立数据库事务，避免单租户异常污染其他租户。
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.runtime_operations import RuntimeAlertRule
from app.services.runtime_operations.alerting import RuntimeAlertEvaluator

logger = logging.getLogger(__name__)


class RuntimeAlertScheduler:
    """按租户周期执行 Runtime Alert Rule 评估。"""

    def __init__(self, poll_interval_seconds: float = 60.0) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    async def tick_once(self) -> dict[str, int]:
        """发现启用告警规则的租户并执行一次告警评估。"""
        async with SessionLocal() as discovery_db:
            result = await discovery_db.execute(
                select(RuntimeAlertRule.tenant_id)
                .where(RuntimeAlertRule.enabled.is_(True))
                .distinct()
            )
            tenant_ids: list[UUID] = list(result.scalars().all())

        evaluated = 0
        transitions = 0
        for tenant_id in tenant_ids:
            async with SessionLocal() as db:
                try:
                    changes = await RuntimeAlertEvaluator(db).evaluate(tenant_id)
                    await db.commit()
                    evaluated += 1
                    transitions += len(changes)
                except Exception:
                    await db.rollback()
                    logger.exception("Runtime alert evaluation failed for tenant %s", tenant_id)
                    raise
        return {"discovered": len(tenant_ids), "evaluated": evaluated, "transitions": transitions}

    async def run_forever(self) -> None:
        """持续运行 Runtime Alert 评估直到收到停止请求。"""
        while not self._stop_event.is_set():
            await self.tick_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """请求停止周期任务。"""
        self._stop_event.set()
