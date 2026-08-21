from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.dependencies.db import SessionLocal
from app.models.workflow import Workflow
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_trigger import WorkflowTriggerService

logger = logging.getLogger(__name__)


class ScheduledTriggerScheduler:
    """Small DB-backed scheduler for the first interval-based Trigger runtime.

    The scheduler deliberately uses the existing WorkflowExecution idempotency
    contract instead of adding scheduler state columns in Phase 1.7-A. Each
    trigger gets one deterministic idempotency key per interval slot, which also
    makes duplicate dispatches from multiple application workers converge on a
    single execution.
    """

    def __init__(self, poll_interval_seconds: float = 5.0):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    @staticmethod
    def interval_slot(now: datetime, interval_seconds: int) -> int:
        if interval_seconds < 1:
            raise ValueError("interval_seconds 必须大于 0")
        timestamp = now.astimezone(UTC).timestamp()
        return int(timestamp // interval_seconds)

    @classmethod
    def idempotency_key(cls, trigger_id, now: datetime, interval_seconds: int) -> str:
        slot = cls.interval_slot(now, interval_seconds)
        return f"scheduled:{trigger_id}:{slot}"

    async def tick_once(self, now: datetime | None = None) -> dict[str, int]:
        """Dispatch all enabled scheduled triggers once and return counters."""
        now = now or datetime.now(UTC)
        counters = {"eligible": 0, "dispatched": 0, "skipped": 0, "failed": 0}

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
                try:
                    config = WorkflowTriggerService.validate_config(trigger.trigger_type, trigger.config or {})
                    idempotency_key = self.idempotency_key(trigger.id, now, config["interval_seconds"])
                    execution_service = WorkflowTriggerService(db)
                    existing = await execution_service.find_execution_by_idempotency_key(
                        workflow.tenant_id, idempotency_key
                    )
                    if existing is not None:
                        counters["skipped"] += 1
                        continue
                    await execution_service.invoke_scheduled(
                        workflow=workflow,
                        trigger=trigger,
                        actor_id=trigger.created_by,
                        input_data={},
                        idempotency_key=idempotency_key,
                    )
                    counters["dispatched"] += 1
                except Exception:
                    await db.rollback()
                    counters["failed"] += 1
                    logger.exception(
                        "Scheduled Trigger dispatch failed",
                        extra={"trigger_id": str(trigger.id), "workflow_id": str(workflow.id)},
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
