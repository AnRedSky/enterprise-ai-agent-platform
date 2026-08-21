from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.dependencies.db import SessionLocal
from app.models.execution import Execution  # noqa: F401 - register legacy execution table for AuditLog FK metadata
from app.models.workflow import Workflow
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_trigger import WorkflowTriggerService

logger = logging.getLogger(__name__)


class ScheduledTriggerScheduler:
    """DB-backed scheduler for interval-based Workflow Triggers.

    Phase 1.7-A-03 adds bounded recovery. Phase 1.7-A-04 treats the database
    idempotency constraint as the cross-worker convergence boundary and treats a
    concurrent Runtime claim as a skip rather than a scheduler failure.
    """

    DEFAULT_RECOVERY_SLOTS = 2
    MAX_RECOVERY_SLOTS = 5

    def __init__(self, poll_interval_seconds: float = 5.0, recovery_slots: int = DEFAULT_RECOVERY_SLOTS):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        if isinstance(recovery_slots, bool) or not 1 <= recovery_slots <= self.MAX_RECOVERY_SLOTS:
            raise ValueError(f"recovery_slots 必须在 1-{self.MAX_RECOVERY_SLOTS} 范围内")
        self.poll_interval_seconds = poll_interval_seconds
        # Preserve the class-level recovery_slots API while making the
        # constructor's recovery_slots setting effective for this worker.
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

    async def tick_once(self, now: datetime | None = None) -> dict[str, int]:
        """Dispatch enabled scheduled triggers for the bounded recovery window."""
        now = now or datetime.now(UTC)
        counters = {"eligible": 0, "dispatched": 0, "skipped": 0, "failed": 0, "recovered": 0, "contention": 0}

        async with SessionLocal() as db:
            result = await db.execute(
                select(WorkflowTrigger, Workflow)
                .join(Workflow, Workflow.id == WorkflowTrigger.workflow_id)
                .where(
                    WorkflowTrigger.trigger_type == "scheduled",
                    WorkflowTrigger.status == "enabled",
                    Workflow.status == "published",
                    Workflow.published_version_id.is_not(None),
                )
                .order_by(WorkflowTrigger.created_at.asc(), WorkflowTrigger.id.asc())
            )
            candidates = result.all()

            for trigger, workflow in candidates:
                counters["eligible"] += 1
                trigger_id = str(trigger.id)
                workflow_id = str(workflow.id)
                try:
                    config = WorkflowTriggerService.validate_config(trigger.trigger_type, trigger.config or {})
                    service = WorkflowTriggerService(db)
                    slots = self.recovery_slots(now, config["interval_seconds"])
                    current_slot = self.interval_slot(now, config["interval_seconds"])
                    for slot in slots:
                        idempotency_key = self.slot_idempotency_key(trigger.id, slot)
                        existing = await service.find_execution_by_idempotency_key(workflow.tenant_id, idempotency_key)
                        if existing is not None:
                            counters["skipped"] += 1
                            continue
                        recovery = slot != current_slot
                        try:
                            await service.invoke_scheduled(
                                workflow=workflow,
                                trigger=trigger,
                                actor_id=trigger.created_by,
                                input_data={"scheduled_slot": slot, "recovery": recovery},
                                idempotency_key=idempotency_key,
                                recovery=recovery,
                            )
                        except HTTPException as exc:
                            if self.is_concurrent_runtime_claim(exc):
                                counters["contention"] += 1
                                continue
                            raise
                        counters["dispatched"] += 1
                        if recovery:
                            counters["recovered"] += 1
                except Exception:
                    await db.rollback()
                    counters["failed"] += 1
                    logger.exception(
                        "Scheduled Trigger dispatch failed",
                        extra={"trigger_id": trigger_id, "workflow_id": workflow_id},
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
