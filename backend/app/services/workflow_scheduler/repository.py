"""Workflow Scheduler 持久化仓储。

职责：封装 Scheduler 状态、租约和执行槽位的 PostgreSQL 原子操作，并持久化 misfire 配置。
边界：不负责时间计算、Trigger 校验或 Workflow 执行；这些职责分别由 Scheduler Contract 与 WorkflowTriggerService 承担。
关键依赖：SQLAlchemy AsyncSession、PostgreSQL ON CONFLICT，以及 Scheduler 持久化模型。

时间边界：Scheduler Runtime 可以使用带 UTC 时区信息的 datetime；本仓储统一在数据库边界
转换为 UTC naive datetime，以匹配 PostgreSQL TIMESTAMP WITHOUT TIME ZONE 字段，避免 asyncpg
在不同 timezone-aware/naive 值之间执行非法运算。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow
from app.models.workflow_scheduler import WorkflowSchedule, WorkflowScheduleSlot
from app.models.workflow_trigger import WorkflowTrigger


class WorkflowSchedulerRepository:
    """Scheduler 持久化仓储，统一提供调度状态、租约、misfire 配置与槽位的数据库边界。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _db_datetime(value: datetime) -> datetime:
        """将调度层 datetime 规范化为 UTC naive，匹配 PostgreSQL 无时区字段。"""
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    async def list_due_scheduled_candidates(
        self,
        *,
        now: datetime,
        limit: int | None = None,
    ) -> list[tuple[WorkflowTrigger, Workflow, WorkflowSchedule]]:
        """原子发现真正到期的 Scheduled Trigger，隔离 disabled/future 与全库无关脏数据。

        Scheduler Runtime 只能消费已经存在的持久化 Schedule；缺失 Schedule 不在 tick
        中隐式初始化，避免一次 tick 将全库所有历史 Scheduled Trigger 人为变成当前到期任务。
        """
        db_now = self._db_datetime(now)
        statement = (
            select(WorkflowTrigger, Workflow, WorkflowSchedule)
            .join(Workflow, Workflow.id == WorkflowTrigger.workflow_id)
            .join(
                WorkflowSchedule,
                (WorkflowSchedule.tenant_id == WorkflowTrigger.tenant_id)
                & (WorkflowSchedule.trigger_id == WorkflowTrigger.id),
            )
            .where(
                WorkflowTrigger.trigger_type == "scheduled",
                WorkflowTrigger.status == "enabled",
                Workflow.status == "published",
                Workflow.published_version_id.is_not(None),
                WorkflowSchedule.enabled.is_(True),
                WorkflowSchedule.status == "enabled",
                WorkflowSchedule.next_run_at <= db_now,
            )
            .order_by(WorkflowSchedule.next_run_at.asc(), WorkflowTrigger.created_at.asc(), WorkflowTrigger.id.asc())
        )
        if limit is not None:
            if isinstance(limit, bool) or limit < 1:
                raise ValueError("limit 必须大于等于 1")
            statement = statement.limit(limit)
        result = await self.db.execute(statement)
        return list(result.all())

    async def get_schedule_for_trigger(self, *, tenant_id: UUID, trigger_id: UUID) -> WorkflowSchedule | None:
        """按 tenant + trigger 获取唯一 Scheduler 状态，tenant 是强制查询边界。"""
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
        misfire_policy: str = "skip",
        catch_up_limit: int = 10,
    ) -> WorkflowSchedule:
        """为 Scheduled Trigger 确保唯一持久化状态；并发首次初始化由数据库唯一键收敛。"""
        existing = await self.get_schedule_for_trigger(tenant_id=tenant_id, trigger_id=trigger_id)
        if existing is not None:
            return existing
        db_now = self._db_datetime(now)
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
                next_run_at=db_now,
                misfire_policy=misfire_policy,
                catch_up_limit=catch_up_limit,
                updated_at=db_now,
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
        misfire_policy: str = "skip",
        catch_up_limit: int = 10,
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
                misfire_policy=misfire_policy,
                catch_up_limit=catch_up_limit,
                updated_at=self._db_datetime(now),
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
        db_now = self._db_datetime(now)
        statement = (
            update(WorkflowSchedule)
            .where(
                WorkflowSchedule.id == schedule_id,
                WorkflowSchedule.tenant_id == tenant_id,
                WorkflowSchedule.enabled.is_(True),
                WorkflowSchedule.status == "enabled",
                WorkflowSchedule.next_run_at <= db_now,
                or_(WorkflowSchedule.lease_expires_at.is_(None), WorkflowSchedule.lease_expires_at <= db_now),
            )
            .values(lease_owner=owner, lease_expires_at=self._db_datetime(lease_expires_at), updated_at=db_now)
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
                next_run_at=self._db_datetime(next_run_at),
                last_run_at=self._db_datetime(last_run_at),
                last_execution_id=last_execution_id,
                lease_owner=None,
                lease_expires_at=None,
                updated_at=self._db_datetime(now),
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
            .values(lease_owner=None, lease_expires_at=None, updated_at=self._db_datetime(now))
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
                planned_at=self._db_datetime(planned_at),
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
