"""Runtime Alert 周期调度。

职责：周期发现启用 Runtime Alert Rule 的租户，并执行确定性的
Metric Sample -> Alert firing/recovery 评估，同时将同一 Durable Runtime
指标快照桥接到进程级 OpenTelemetry Meter。

边界：不执行外部网络调用，不绕过 Alert Evaluator 修改告警事实；每个 tenant
使用独立数据库事务，避免单租户异常污染其他租户。Telemetry 只消费已经持久化
的运维事实，不建立第二套业务指标状态。

关键依赖：SQLAlchemy AsyncSession、Runtime Alert Evaluator、Runtime Operations
Service 与 RuntimeTelemetry。
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.runtime_operations import RuntimeAlertRule
from app.services.runtime_operations.alerting import RuntimeAlertEvaluator
from app.services.runtime_operations.service import RuntimeOperationsService
from app.services.runtime_operations.telemetry import RuntimeTelemetry

logger = logging.getLogger(__name__)


class RuntimeAlertScheduler:
    """按租户周期执行 Runtime Alert 评估并同步标准观测指标。"""

    def __init__(self, poll_interval_seconds: float = 60.0) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()
        self._telemetry: RuntimeTelemetry | None = None

    def set_telemetry(self, telemetry: RuntimeTelemetry) -> None:
        """注入进程级 Telemetry Provider。

        Args:
            telemetry: Scheduler Service 生命周期创建并统一持有的 RuntimeTelemetry。

        Returns:
            无返回值。

        设计意图：Telemetry Provider 必须由进程生命周期管理，不能在每个 tenant
        或每轮调度中重复创建，避免 SDK 资源泄漏及观测出口碎片化。
        """
        self._telemetry = telemetry

    async def _sync_telemetry(self, tenant_id: UUID, db) -> None:
        """从 Durable Runtime facts 生成当前租户的 SDK Meter 快照。"""
        if self._telemetry is None:
            return
        overview = await RuntimeOperationsService(db).overview(tenant_id, window_hours=24)
        slo = overview["slo"]
        values: dict[str, float | int | None] = {
            "runtime.delivery.success_percent": slo["delivery_success_percent"],
            "runtime.delivery.retry_count": overview["deliveries"]["retry_count"],
            "runtime.delivery.dead_letter_count": overview["deliveries"]["dead_letter_count"],
        }
        if slo["p95_delivery_latency_ms"] is not None:
            values["runtime.delivery.p95_latency_ms"] = slo["p95_delivery_latency_ms"]
        self._telemetry.record(tenant_id, values)

    async def tick_once(self) -> dict[str, int]:
        """发现启用告警规则的租户并执行一次告警评估及观测同步。"""
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
                    await self._sync_telemetry(tenant_id, db)
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
