"""Workflow Scheduler 持久化仓储。

职责：封装 Scheduler 状态、租约和执行槽位的 PostgreSQL 原子操作。
边界：不负责时间计算、Trigger 校验或 Workflow 执行；这些职责分别由 Scheduler Contract 与 WorkflowTriggerService 承担。
关键依赖：SQLAlchemy AsyncSession、PostgreSQL ON CONFLICT，以及 Scheduler 持久化模型。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_scheduler import WorkflowSchedule, WorkflowScheduleSlot


class WorkflowSchedulerRepository:
    """Scheduler 持久化仓储，统一提供调度状态、租约与槽位的数据库边界。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_schedule_for_trigger(self, *, tenant_id: UUID, trigger_id: UUID) -> WorkflowSchedule | None:
        """按 tenant + trigger 获取唯一 Scheduler 状态。"""
        result = await self.db.execute(
            select(WorkflowSchedule).where(
                WorkflowSchedule.tenant_id == tenant_id,
                WorkflowSchedule.trigger_id == trigger_id,
            )
        )
        return result.scalar_one_or_none()

    async def ensure_schedule(
        self,
        *,
        tenant_id: UUID,
        trigger_id: UUID,
        workflow_id: UUID,
        timezone: str,
        interval_seconds: int,
        enabled: bool,
        now: datetime,
    ) -> WorkflowSchedule:
        """为 Scheduled Trigger 确保唯一持久化状态；并发首次初始化由数据库唯一键收敛。"""
        existing = await self.get_schedule_for_trigger(tenant_id=tenant_id, trigger_id=trigger_id)
        if existing is not None:
            return existing
        statement = (
            pg_insert(WorkflowSchedule)
            .values(
                tenant_id=tenant_id,
                trigger_id=trigger_id,
                workflow_id=workflow_id,
                enabled=enabled,
                status="enabled" if enabled else "disabled",
                timezone=timezone,
                schedule_expression=f"interval:{interval_seconds}",
                next_run_at=now,
                misfire_policy="skip",
                catch_up_limit=10,
                updated_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_workflow_schedule_tenant_trigger")
            .returning(WorkflowSchedule.id)
        )
        schedule_id = (await self.db.execute(statement)).scalar_one_or_none()
        if schedule_id is None:
            existing = await self.get_schedule_for_trigger(tenant_id=tenant_id, trigger_id=trigger_id)
            if existing is None:
                raise RuntimeError("Scheduler 状态初始化未收敛")
            return existing
        return (
            await self.db.execute(select(WorkflowSchedule).where(WorkflowSchedule.id == schedule_id))
        ).scalar_one()

    async def sync_schedule_config(
        self,
        *,
        schedule_id: UUID,
        tenant_id: UUID,
        timezone: str,
        interval_seconds: int,
        enabled: bool,
        now: datetime,
    ) -> WorkflowSchedule | None:
        """更新已存在 Scheduler 状态的配置，不重置已计算的 next_run_at。"""
        statement = (
            update(WorkflowSchedule)
            .where(
                WorkflowSchedule.id == schedule_id,
                WorkflowSchedule.tenant_id == tenant_id,
            )
            .values(
                enabled=enabled,
                status="enabled" if enabled else "disabled",
                timezone=timezone,
                schedule_expression=f"interval:{interval_seconds}",
                updated_at=now,
            )
            .returning(WorkflowSchedule)
            .execution_options(synchronize_session=False)
        )
        return (await self.db.execute(statement)).scalar_one_or_none()

    async def claim_due_lease(
        self,
        *,
        schedule_id: UUID,
        tenant_id: UUID,
        owner: str,
        now: datetime,
        lease_expires_at: datetime,
    ) -> WorkflowSchedule | None:
        """使用单条 UPDATE 原子抢占到期调度，避免先查询再更新产生竞态。"""
        statement = (
            update(WorkflowSchedule)
            .where(
                WorkflowSchedule.id == schedule_id,
                WorkflowSchedule.tenant_id == tenant_id,
                WorkflowSchedule.enabled.is_(True),
                WorkflowSchedule.status == "enabled",
                WorkflowSchedule.next_run_at <= now,
                or_(WorkflowSchedule.lease_expires_at.is_(None), WorkflowSchedule.lease_expires_at <= now),
            )
            .values(lease_owner=owner, lease_expires_at=lease_expires_at, updated_at=now)
            .returning(WorkflowSchedule)
            .execution_options(synchronize_session=False)
        )
        return (await self.db.execute(statement)).scalar_one_or_none()

    async def advance_schedule(
        self,
        *,
        schedule_id: UUID,
        tenant_id: UUID,
        owner: str,
        now: datetime,
        next_run_at: datetime,
        last_run_at: datetime,
        last_execution_id: UUID | None,
    ) -> WorkflowSchedule | None:
        """仅允许当前 lease owner 推进调度状态并释放租约。"""
        statement = (
            update(WorkflowSchedule)
            .where(
                WorkflowSchedule.id == schedule_id,
                WorkflowSchedule.tenant_id == tenant_id,
                WorkflowSchedule.lease_owner == owner,
            )
            .values(
                next_run_at=next_run_at,
                last_run_at=last_run_at,
                last_execution_id=last_execution_id,
                lease_owner=None,
                lease_expires_at=None,
                updated_at=now,
            )
            .returning(WorkflowSchedule)
            .execution_options(synchronize_session=False)
        )
        return (await self.db.execute(statement)).scalar_one_or_none()

    async def release_lease(self, *, schedule_id: UUID, tenant_id: UUID, owner: str, now: datetime) -> bool:
        """只允许当前 owner 释放租约，防止旧 worker 清理新 owner 的租约。"""
        statement = (
            update(WorkflowSchedule)
            .where(
                WorkflowSchedule.id == schedule_id,
                WorkflowSchedule.tenant_id == tenant_id,
                WorkflowSchedule.lease_owner == owner,
            )
            .values(lease_owner=None, lease_expires_at=None, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(statement)
        return result.rowcount == 1

    async def claim_schedule_slot(
        self,
        *,
        tenant_id: UUID,
        trigger_id: UUID,
        workflow_id: UUID,
        schedule_slot_key: str,
        planned_at: datetime,
        scheduler_owner: str,
    ) -> WorkflowScheduleSlot | None:
        """使用唯一键执行槽位幂等抢占，数据库唯一约束是最终一致性边界。"""
        statement = (
            pg_insert(WorkflowScheduleSlot)
            .values(
                tenant_id=tenant_id,
                trigger_id=trigger_id,
                workflow_id=workflow_id,
                schedule_slot_key=schedule_slot_key,
                planned_at=planned_at,
                scheduler_owner=scheduler_owner,
            )
            .on_conflict_do_nothing(index_elements=[WorkflowScheduleSlot.schedule_slot_key])
            .returning(WorkflowScheduleSlot)
        )
        result = await self.db.execute(statement)
        claimed = result.scalar_one_or_none()
        if claimed is not None:
            return claimed
        existing = await self.db.execute(
            select(WorkflowScheduleSlot).where(
                WorkflowScheduleSlot.tenant_id == tenant_id,
                WorkflowScheduleSlot.schedule_slot_key == schedule_slot_key,
            )
        )
        return existing.scalar_one_or_none()

    async def bind_execution_to_slot(self, *, slot_id: UUID, workflow_execution_id: UUID) -> WorkflowScheduleSlot | None:
        """在槽位已成功抢占后绑定 WorkflowExecution，保持调度入口与执行身份可追溯。"""
        statement = (
            update(WorkflowScheduleSlot)
            .where(
                WorkflowScheduleSlot.id == slot_id,
                WorkflowScheduleSlot.workflow_execution_id.is_(None),
            )
            .values(workflow_execution_id=workflow_execution_id)
            .returning(WorkflowScheduleSlot)
            .execution_options(synchronize_session=False)
        )
        return (await self.db.execute(statement)).scalar_one_or_none()
