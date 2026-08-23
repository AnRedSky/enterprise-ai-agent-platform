from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_scheduler import WorkflowSchedule, WorkflowScheduleSlot


class WorkflowSchedulerRepository:
    """Scheduler 持久化仓储，封装租约与槽位幂等的数据库原子操作。"""

    def __init__(self, db: AsyncSession):
        self.db = db

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
                or_(
                    WorkflowSchedule.lease_expires_at.is_(None),
                    WorkflowSchedule.lease_expires_at <= now,
                ),
            )
            .values(lease_owner=owner, lease_expires_at=lease_expires_at, updated_at=now)
            .returning(WorkflowSchedule)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def release_lease(
        self,
        *,
        schedule_id: UUID,
        tenant_id: UUID,
        owner: str,
        now: datetime,
    ) -> bool:
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

    async def bind_execution_to_slot(
        self,
        *,
        slot_id: UUID,
        workflow_execution_id: UUID,
    ) -> WorkflowScheduleSlot | None:
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
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()
