"""Workflow Scheduler Runtime：负责已启用 Scheduled Trigger 的轮询、恢复与幂等分发。

模块职责：读取可调度 Trigger、计算恢复槽位，并委托既有 WorkflowTriggerService 执行调度。
边界：不创建第二套数据库 Session、不实现新的 Workflow 执行逻辑；数据库 Session 统一由 Infrastructure 层提供，实际执行继续复用 WorkflowTriggerService。
关键依赖：`app.infrastructure.db.SessionLocal`、`WorkflowTriggerService` 与 Scheduler Contract。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.execution import Execution  # noqa: F401 - 注册 AuditLog 外键元数据
from app.models.workflow import Workflow
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_trigger import WorkflowTriggerService

logger = logging.getLogger(__name__)


class ScheduledTriggerScheduler:
    """现有 Scheduled Trigger 的数据库轮询调度器。"""

    DEFAULT_RECOVERY_SLOTS = 2
    MAX_RECOVERY_SLOTS = 5

    def __init__(self, poll_interval_seconds: float = 5.0, recovery_slots: int = DEFAULT_RECOVERY_SLOTS):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        if isinstance(recovery_slots, bool) or not 1 <= recovery_slots <= self.MAX_RECOVERY_SLOTS:
            raise ValueError(f"recovery_slots 必须在 1-{self.MAX_RECOVERY_SLOTS} 范围内")
        self.poll_interval_seconds = poll_interval_seconds
        self.max_recovery_slots = recovery_slots
        self.recovery_slots = lambda now, interval_seconds: type(self).recovery_slots(
            now, interval_seconds, self.max_recovery_slots
        )
        self._stop_event = asyncio.Event()

    @staticmethod
    def interval_slot(now: datetime, interval_seconds: int) -> int:
        if interval_seconds < 1:
            raise ValueError("interval_seconds 必须大于 0")
        timestamp = now.astimezone(UTC).timestamp()
        return int(timestamp // interval_seconds)

    @classmethod
    def slot_idempotency_key(cls, trigger_id, slot: int) -> str:
        return f"scheduled:{trigger_id}:{slot}"

    @classmethod
    def idempotency_key(cls, trigger_id, now: datetime, interval_seconds: int) -> str:
        return cls.slot_idempotency_key(trigger_id, cls.interval_slot(now, interval_seconds))

    @classmethod
    def recovery_slots(
        cls,
        now: datetime,
        interval_seconds: int,
        max_recovery_slots: int = DEFAULT_RECOVERY_SLOTS,
    ) -> list[int]:
        if isinstance(max_recovery_slots, bool) or not 1 <= max_recovery_slots <= cls.MAX_RECOVERY_SLOTS:
            raise ValueError(f"max_recovery_slots 必须在 1-{cls.MAX_RECOVERY_SLOTS} 范围内")
        current = cls.interval_slot(now, interval_seconds)
        return list(range(current - max_recovery_slots + 1, current + 1))

    @staticmethod
    def is_concurrent_runtime_claim(exc: BaseException) -> bool:
        return isinstance(exc, HTTPException) and exc.status_code == 409 and "只有 pending Execution 可以启动 Runtime" in str(exc.detail)

    @staticmethod
    def is_scheduled_claim_contention(exc: BaseException) -> bool:
        return isinstance(exc, HTTPException) and exc.status_code == 409 and "Scheduled Trigger Idempotency claim contention" in str(exc.detail)

    @classmethod
    def is_recovery_slot(
        cls,
        now: datetime,
        slot: int,
        interval_seconds: int,
        trigger_created_at: datetime | None,
    ) -> bool:
        current_slot = cls.interval_slot(now, interval_seconds)
        if slot == current_slot:
            return False
        # 新建 Trigger 在创建时所在槽位视为正常首次调度，不作为历史恢复槽位。
        if trigger_created_at is not None:
            created_at = trigger_created_at.replace(tzinfo=UTC) if trigger_created_at.tzinfo is None else trigger_created_at.astimezone(UTC)
            if now.astimezone(UTC) >= created_at and slot == cls.interval_slot(created_at, interval_seconds):
                return False
        return True

    async def tick_once(self, now: datetime | None = None) -> dict[str, int]:
        """在受控恢复窗口内分发已启用的 Scheduled Trigger。"""
        now = now or datetime.now(UTC)
        counters = {"eligible": 0, "dispatched": 0, "skipped": 0, "failed": 0, "recovered": 0, "contention": 0}
        # 先只读取稳定主键，再让每个 Trigger 使用独立会话处理，避免回滚影响后续候选对象。
        async with SessionLocal() as discovery_db:
            result = await discovery_db.execute(
                select(WorkflowTrigger.id)
                .join(Workflow, Workflow.id == WorkflowTrigger.workflow_id)
                .where(
                    WorkflowTrigger.trigger_type == "scheduled",
                    WorkflowTrigger.status == "enabled",
                    Workflow.status == "published",
                    Workflow.published_version_id.is_not(None),
                )
                .order_by(WorkflowTrigger.created_at.asc(), WorkflowTrigger.id.asc())
            )
            trigger_ids = list(result.scalars().all())

        for trigger_id in trigger_ids:
            async with SessionLocal() as db:
                trigger_id_text = str(trigger_id)
                workflow_id_text = "unknown"
                try:
                    candidate = (
                        await db.execute(
                            select(WorkflowTrigger, Workflow)
                            .join(Workflow, Workflow.id == WorkflowTrigger.workflow_id)
                            .where(
                                WorkflowTrigger.id == trigger_id,
                                WorkflowTrigger.trigger_type == "scheduled",
                                WorkflowTrigger.status == "enabled",
                                Workflow.status == "published",
                                Workflow.published_version_id.is_not(None),
                            )
                        )
                    ).one_or_none()
                    if candidate is None:
                        continue
                    trigger, workflow = candidate
                    workflow_id_text = str(workflow.id)
                    counters["eligible"] += 1
                    config = WorkflowTriggerService.validate_config(trigger.trigger_type, trigger.config or {})
                    service = WorkflowTriggerService(db)
                    for slot in self.recovery_slots(now, config["interval_seconds"]):
                        idempotency_key = self.slot_idempotency_key(trigger.id, slot)
                        recovery = self.is_recovery_slot(now, slot, config["interval_seconds"], trigger.created_at)
                        try:
                            _, created = await service.invoke_scheduled(
                                workflow=workflow,
                                trigger=trigger,
                                actor_id=trigger.created_by,
                                input_data={"scheduled_slot": slot, "recovery": recovery},
                                idempotency_key=idempotency_key,
                                recovery=recovery,
                                return_created=True,
                            )
                        except HTTPException as exc:
                            if self.is_concurrent_runtime_claim(exc) or self.is_scheduled_claim_contention(exc):
                                counters["contention"] += 1
                                continue
                            raise
                        if not created:
                            counters["skipped"] += 1
                            continue
                        counters["dispatched"] += 1
                        if recovery:
                            counters["recovered"] += 1
                except Exception:
                    await db.rollback()
                    counters["failed"] += 1
                    logger.exception(
                        "Scheduled Trigger dispatch failed",
                        extra={"trigger_id": trigger_id_text, "workflow_id": workflow_id_text},
                    )
        return counters

    async def run_forever(self) -> None:
        self._stop_event.clear()
        while not self._stop_event.is_set():
            try:
                await self.tick_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduled Trigger scheduler tick failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        self._stop_event.set()
