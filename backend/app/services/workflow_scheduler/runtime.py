"""Workflow Scheduler Runtime：负责已启用 Scheduled Trigger 的持久化调度与幂等分发。

职责：从 PostgreSQL 持久化状态恢复到期任务，使用 lease + slot 完成多实例 ownership、租户隔离与 misfire 补偿。
边界：不创建第二套数据库 Session、不复制 Workflow 执行逻辑；实际执行继续复用 WorkflowTriggerService。
关键依赖：`app.infrastructure.db.SessionLocal`、WorkflowSchedulerRepository、Trigger 领域服务与 Scheduler Contract。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.execution import Execution  # noqa: F401 - 注册 AuditLog 外键元数据
from app.models.workflow import Workflow
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_scheduler.misfire import build_due_slots, choose_misfire_slots, next_run_after_misfire
from app.services.workflow_scheduler.models import MisfirePolicy
from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository
from app.services.trigger import WorkflowTriggerService

logger = logging.getLogger(__name__)


class _RecoverySlotsDescriptor:
    """同时支持实例配置调用与类级纯函数调用，避免为同一槽位规则保留两套实现。"""

    def __get__(self, instance, owner):
        def calculate(now: datetime, interval_seconds: int, max_recovery_slots: int | None = None) -> list[int]:
            limit = (
                instance.max_recovery_slots
                if instance is not None and max_recovery_slots is None
                else owner.DEFAULT_RECOVERY_SLOTS
                if max_recovery_slots is None
                else max_recovery_slots
            )
            if isinstance(limit, bool) or not 1 <= limit <= owner.MAX_RECOVERY_SLOTS:
                raise ValueError(f"max_recovery_slots 必须在 1-{owner.MAX_RECOVERY_SLOTS} 范围内")
            current = owner.interval_slot(now, interval_seconds)
            return list(range(current - limit + 1, current + 1))

        return calculate


class ScheduledTriggerScheduler:
    """基于 PostgreSQL 持久化状态运行 Scheduled Trigger。"""

    DEFAULT_RECOVERY_SLOTS = 2
    MAX_RECOVERY_SLOTS = 5
    DEFAULT_LEASE_SECONDS = 30

    def __init__(
        self,
        poll_interval_seconds: float = 5.0,
        recovery_slots: int = DEFAULT_RECOVERY_SLOTS,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        if isinstance(recovery_slots, bool) or not 1 <= recovery_slots <= self.MAX_RECOVERY_SLOTS:
            raise ValueError(f"recovery_slots 必须在 1-{self.MAX_RECOVERY_SLOTS} 范围内")
        if isinstance(lease_seconds, bool) or lease_seconds < 1:
            raise ValueError("lease_seconds 必须大于 0")
        self.poll_interval_seconds = poll_interval_seconds
        self.max_recovery_slots = recovery_slots
        self.lease_seconds = lease_seconds
        self.owner = f"scheduler:{uuid4()}"
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

    @staticmethod
    def is_recovery_slot(planned_at: datetime, now: datetime, interval_seconds: int) -> bool:
        """仅把早于当前 interval 槽位的历史计划标记为 recovery，当前槽位不继承 misfire 状态。"""
        return ScheduledTriggerScheduler.interval_slot(planned_at, interval_seconds) < ScheduledTriggerScheduler.interval_slot(
            now, interval_seconds
        )

    recovery_slots = _RecoverySlotsDescriptor()

    @staticmethod
    def is_concurrent_runtime_claim(exc: BaseException) -> bool:
        return isinstance(exc, HTTPException) and exc.status_code == 409 and "只有 pending Execution 可以启动 Runtime" in str(exc.detail)

    @staticmethod
    def is_scheduled_claim_contention(exc: BaseException) -> bool:
        return isinstance(exc, HTTPException) and exc.status_code == 409 and "Scheduled Trigger Idempotency claim contention" in str(exc.detail)

    @staticmethod
    def parse_interval(schedule_expression: str) -> int:
        """解析 Scheduler 自身产生的 interval 表达式，避免复制 Trigger 配置校验规则。"""
        prefix = "interval:"
        if not schedule_expression.startswith(prefix):
            raise ValueError(f"不支持的 Scheduler expression: {schedule_expression}")
        interval_seconds = int(schedule_expression[len(prefix) :])
        if interval_seconds < 1:
            raise ValueError("Scheduler interval 必须大于 0")
        return interval_seconds

    @staticmethod
    def planned_slot_key(trigger_id, planned_at: datetime, interval_seconds: int) -> str:
        """使用统一的时间槽编号生成幂等键，确保 Runtime 与公开 Scheduler Contract 使用同一键空间。"""
        return ScheduledTriggerScheduler.idempotency_key(trigger_id, planned_at, interval_seconds)

    @classmethod
    def next_run_after_skip(cls, planned_at: datetime, now: datetime, interval_seconds: int) -> datetime:
        """首版 skip 策略的纯计算入口：跳过历史积压并从未来 interval 继续。"""
        candidate = planned_at + timedelta(seconds=interval_seconds)
        if candidate <= now:
            return now + timedelta(seconds=interval_seconds)
        return candidate

    async def tick_once(self, now: datetime | None = None) -> dict[str, int]:
        """从持久化 Scheduler 状态抢占并执行到期槽位。"""
        now = now or datetime.now(UTC)
        counters = {"eligible": 0, "dispatched": 0, "skipped": 0, "failed": 0, "recovered": 0, "contention": 0}

        async with SessionLocal() as discovery_db:
            result = await discovery_db.execute(
                select(WorkflowTrigger.id)
                .join(Workflow, Workflow.id == WorkflowTrigger.workflow_id)
                .where(
                    WorkflowTrigger.trigger_type == "scheduled",
                    WorkflowTrigger.status.in_(["enabled", "disabled"]),
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
                repository = WorkflowSchedulerRepository(db)
                schedule = None
                try:
                    candidate = (
                        await db.execute(
                            select(WorkflowTrigger, Workflow)
                            .join(Workflow, Workflow.id == WorkflowTrigger.workflow_id)
                            .where(
                                WorkflowTrigger.id == trigger_id,
                                WorkflowTrigger.trigger_type == "scheduled",
                                WorkflowTrigger.status.in_(["enabled", "disabled"]),
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
                    schedule = await repository.ensure_schedule(
                        tenant_id=trigger.tenant_id, trigger_id=trigger.id, workflow_id=workflow.id,
                        timezone=config["timezone"], interval_seconds=config["interval_seconds"],
                        enabled=trigger.status == "enabled", now=now,
                        misfire_policy=config["misfire_policy"], catch_up_limit=config["catch_up_limit"],
                    )
                    await repository.sync_schedule_config(
                        schedule_id=schedule.id, tenant_id=trigger.tenant_id,
                        timezone=config["timezone"], interval_seconds=config["interval_seconds"],
                        enabled=trigger.status == "enabled", now=now,
                        misfire_policy=config["misfire_policy"], catch_up_limit=config["catch_up_limit"],
                    )
                    await db.commit()

                    if trigger.status != "enabled":
                        counters["skipped"] += 1
                        continue

                    claimed = await repository.claim_due_lease(
                        schedule_id=schedule.id, tenant_id=trigger.tenant_id, owner=self.owner, now=now,
                        lease_expires_at=now + timedelta(seconds=self.lease_seconds),
                    )
                    if claimed is None:
                        counters["contention"] += 1
                        await db.rollback()
                        continue

                    planned_at = claimed.next_run_at.replace(tzinfo=UTC) if claimed.next_run_at.tzinfo is None else claimed.next_run_at.astimezone(UTC)
                    policy = MisfirePolicy(claimed.misfire_policy)
                    due_slots = build_due_slots(trigger.id, planned_at, now, config["interval_seconds"], limit=config["catch_up_limit"] + 2)
                    selected_slots = due_slots if len(due_slots) == 1 else choose_misfire_slots(due_slots, policy, catch_up_limit=config["catch_up_limit"])
                    has_misfire = len(due_slots) > 1 or (planned_at < now - timedelta(seconds=config["interval_seconds"]))

                    latest_execution = None
                    for slot in selected_slots:
                        slot_key = self.planned_slot_key(trigger.id, slot.planned_at, config["interval_seconds"])
                        slot_recovery = self.is_recovery_slot(slot.planned_at, now, config["interval_seconds"])
                        slot_number = self.interval_slot(slot.planned_at, config["interval_seconds"])
                        slot_record = await repository.claim_schedule_slot(
                            tenant_id=trigger.tenant_id, trigger_id=trigger.id, workflow_id=workflow.id,
                            schedule_slot_key=slot_key, planned_at=slot.planned_at.replace(tzinfo=None), scheduler_owner=self.owner,
                        )
                        if slot_record is None:
                            raise RuntimeError("Scheduler 槽位 claim 未收敛")

                        execution = None
                        created = False
                        if slot_record.workflow_execution_id is not None:
                            execution = await WorkflowTriggerService(db).find_execution_by_idempotency_key(trigger.tenant_id, slot_key)
                        else:
                            service = WorkflowTriggerService(db)
                            try:
                                execution, created = await service.invoke_scheduled(
                                    workflow=workflow, trigger=trigger, actor_id=trigger.created_by,
                                    input_data={"scheduled_slot": slot_number, "planned_at": slot.planned_at.isoformat(), "recovery": slot_recovery},
                                    idempotency_key=slot_key, recovery=slot_recovery, return_created=True,
                                )
                            except HTTPException as exc:
                                if self.is_concurrent_runtime_claim(exc) or self.is_scheduled_claim_contention(exc):
                                    counters["contention"] += 1
                                    await db.rollback()
                                    continue
                                raise
                            if execution is not None:
                                await repository.bind_execution_to_slot(slot_id=slot_record.id, workflow_execution_id=execution.id)
                        if execution is not None:
                            latest_execution = execution
                        if created:
                            counters["dispatched"] += 1
                        else:
                            counters["skipped"] += 1

                    if len(due_slots) > 1:
                        next_run_at = next_run_after_misfire(selected_slots, policy, now, config["interval_seconds"])
                    else:
                        next_run_at = planned_at + timedelta(seconds=config["interval_seconds"])
                    advanced = await repository.advance_schedule(
                        schedule_id=claimed.id, tenant_id=trigger.tenant_id, owner=self.owner, now=now,
                        next_run_at=next_run_at.replace(tzinfo=None),
                        last_run_at=(selected_slots[-1].planned_at if selected_slots else planned_at).replace(tzinfo=None),
                        last_execution_id=latest_execution.id if latest_execution is not None else claimed.last_execution_id,
                    )
                    if advanced is None:
                        counters["contention"] += 1
                        await db.rollback()
                        continue
                    await db.commit()
                    if has_misfire:
                        counters["recovered"] += 1
                except Exception:
                    await db.rollback()
                    if schedule is not None:
                        try:
                            await repository.release_lease(schedule_id=schedule.id, tenant_id=schedule.tenant_id, owner=self.owner, now=now)
                            await db.commit()
                        except Exception:
                            await db.rollback()
                    counters["failed"] += 1
                    logger.exception("Scheduled Trigger dispatch failed", extra={"trigger_id": trigger_id_text, "workflow_id": workflow_id_text})
        return counters

    async def run_forever(self) -> None:
        """持续轮询 Scheduler，生命周期停止由 stop() 控制。"""
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
        """请求结束后台轮询循环。"""
        self._stop_event.set()
