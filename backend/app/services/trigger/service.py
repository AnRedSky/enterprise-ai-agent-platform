"""Trigger 生命周期与执行入口服务。

职责：管理 manual/scheduled/webhook Trigger 的查询、创建、更新、删除和触发执行入口。
边界：不承担 Workflow Registry、Execution 状态机或 Scheduler 调度算法；Scheduled Trigger 负责创建 pending Execution 与首个 Durable Frontier，实际执行交给独立 Worker Service。
关键依赖：Workflow/WorkflowTrigger ORM、Workflow Execution/Governance 服务、Trigger 配置契约与 Workflow Runtime。
"""

from __future__ import annotations

from datetime import UTC, datetime
import uuid
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trigger import WorkflowTrigger
from app.runtime.workflow import WorkflowRuntime
from app.services.integration.publisher import RuntimeIntegrationEventPublisher
from app.services.trigger.schedule import validate_trigger_config
from app.services.workflow import WorkflowExecutionService, WorkflowGovernanceService
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier
from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository


class WorkflowTriggerService:
    """Workflow Trigger 生命周期、配置校验与执行任务创建服务。"""

    ALLOWED_TYPES = {"manual", "scheduled", "webhook"}
    ALLOWED_STATUSES = {"enabled", "disabled"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.governance = WorkflowGovernanceService(db)

    async def list(self, workflow: Workflow) -> list[WorkflowTrigger]:
        result = await self.db.execute(
            select(WorkflowTrigger)
            .where(WorkflowTrigger.tenant_id == workflow.tenant_id, WorkflowTrigger.workflow_id == workflow.id)
            .order_by(WorkflowTrigger.created_at.asc(), WorkflowTrigger.id.asc())
        )
        return list(result.scalars().all())

    async def get(self, workflow: Workflow, trigger_id: UUID) -> WorkflowTrigger:
        trigger = (
            await self.db.execute(
                select(WorkflowTrigger).where(
                    WorkflowTrigger.id == trigger_id,
                    WorkflowTrigger.tenant_id == workflow.tenant_id,
                    WorkflowTrigger.workflow_id == workflow.id,
                )
            )
        ).scalar_one_or_none()
        if trigger is None:
            raise HTTPException(404, "Workflow Trigger 不存在")
        return trigger

    async def find_execution_by_idempotency_key(self, tenant_id: UUID, idempotency_key: str) -> WorkflowExecution | None:
        return (
            await self.db.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.tenant_id == tenant_id,
                    WorkflowExecution.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()

    @classmethod
    def validate_type(cls, trigger_type: str) -> str:
        if trigger_type not in cls.ALLOWED_TYPES:
            raise HTTPException(422, "Trigger type 必须为 manual、scheduled 或 webhook")
        return trigger_type

    @classmethod
    def validate_status(cls, status: str) -> str:
        if status not in cls.ALLOWED_STATUSES:
            raise HTTPException(422, "Trigger status 必须为 enabled 或 disabled")
        return status

    @classmethod
    def validate_config(cls, trigger_type: str, config: dict) -> dict:
        cls.validate_type(trigger_type)
        try:
            return validate_trigger_config(trigger_type, config)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    async def _sync_scheduler_state(self, trigger: WorkflowTrigger, config: dict, *, now: datetime) -> None:
        """让 Scheduled Trigger 生命周期与唯一持久化 Schedule 保持同一事务边界。"""
        if trigger.trigger_type != "scheduled":
            return
        repository = WorkflowSchedulerRepository(self.db)
        schedule = await repository.get_schedule_for_trigger(
            tenant_id=trigger.tenant_id,
            trigger_id=trigger.id,
        )
        if schedule is None:
            await repository.ensure_schedule(
                tenant_id=trigger.tenant_id,
                trigger_id=trigger.id,
                workflow_id=trigger.workflow_id,
                timezone=config["timezone"],
                interval_seconds=config["interval_seconds"],
                enabled=trigger.status == "enabled",
                now=now,
                misfire_policy=config["misfire_policy"],
                catch_up_limit=config["catch_up_limit"],
            )
            return
        await repository.sync_schedule_config(
            schedule_id=schedule.id,
            tenant_id=trigger.tenant_id,
            timezone=config["timezone"],
            interval_seconds=config["interval_seconds"],
            enabled=trigger.status == "enabled",
            now=now,
            misfire_policy=config["misfire_policy"],
            catch_up_limit=config["catch_up_limit"],
        )

    async def create(self, workflow: Workflow, actor_id: UUID, name: str, trigger_type: str, config: dict) -> WorkflowTrigger:
        if workflow.status == "archived":
            raise HTTPException(409, "归档 Workflow 不允许创建 Trigger")
        self.validate_type(trigger_type)
        name = name.strip()
        if not name:
            raise HTTPException(422, "Trigger name 不能为空")
        config = self.validate_config(trigger_type, config)
        trigger = WorkflowTrigger(
            tenant_id=workflow.tenant_id,
            workflow_id=workflow.id,
            name=name,
            trigger_type=trigger_type,
            status="enabled",
            created_by=actor_id,
            config=config,
        )
        self.db.add(trigger)
        try:
            await self.db.flush()
            await self._sync_scheduler_state(trigger, config, now=datetime.now(UTC))
            await self.db.commit()
        except Exception as exc:
            from sqlalchemy.exc import IntegrityError
            if isinstance(exc, IntegrityError):
                await self.db.rollback()
                raise HTTPException(409, "同一 Workflow 下 Trigger name 已存在") from exc
            raise
        await self.db.refresh(trigger)
        return trigger

    async def update(self, trigger: WorkflowTrigger, name: str | None, status: str | None, config: dict | None, *, commit: bool = True) -> WorkflowTrigger:
        """更新 Trigger，并允许调用方控制事务提交边界。"""
        if name is not None:
            name = name.strip()
            if not name:
                raise HTTPException(422, "Trigger name 不能为空")
            trigger.name = name
        if status is not None:
            trigger.status = self.validate_status(status)
        if config is not None:
            candidate = dict(config)
            if trigger.trigger_type == "webhook" and "secret" not in candidate and "secret_hash" not in candidate:
                candidate["secret_hash"] = (trigger.config or {}).get("secret_hash")
            candidate.pop("secret_configured", None)
            trigger.config = self.validate_config(trigger.trigger_type, candidate)
        if trigger.trigger_type == "scheduled":
            await self._sync_scheduler_state(trigger, trigger.config or {}, now=datetime.now(UTC))
        if commit:
            try:
                await self.db.commit()
            except Exception as exc:
                from sqlalchemy.exc import IntegrityError
                if isinstance(exc, IntegrityError):
                    await self.db.rollback()
                    raise HTTPException(409, "同一 Workflow 下 Trigger name 已存在") from exc
                raise
            await self.db.refresh(trigger)
        else:
            await self.db.flush()
        return trigger

    async def delete(self, trigger: WorkflowTrigger, *, commit: bool = True) -> None:
        """删除 Trigger，并允许 Operator Governance 将删除与审计放入同一事务。"""
        await self.db.delete(trigger)
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

    async def _get_published_version(self, workflow: Workflow) -> WorkflowVersion:
        if workflow.status != "published" or workflow.published_version_id is None:
            raise HTTPException(409, "Trigger 只能调用已发布 Workflow")
        version = (await self.db.execute(select(WorkflowVersion).where(
            WorkflowVersion.id == workflow.published_version_id, WorkflowVersion.workflow_id == workflow.id
        ))).scalar_one_or_none()
        if version is None or version.status != "published":
            raise HTTPException(409, "Workflow Published Version 不可用")
        return version

    async def invoke_scheduled(self, workflow: Workflow, trigger: WorkflowTrigger, actor_id: UUID, input_data: dict,
                               idempotency_key: str, recovery: bool = False, return_created: bool = False):
        """为 Scheduled Trigger 创建 pending Execution 与首个 Durable Frontier。"""
        if trigger.status != "enabled":
            raise HTTPException(409, "Trigger 已禁用")
        if trigger.trigger_type != "scheduled":
            raise HTTPException(409, "当前 Trigger 类型不是 scheduled")
        config = self.validate_config(trigger.trigger_type, trigger.config or {})
        if not idempotency_key:
            raise HTTPException(422, "Scheduled Trigger 必须提供调度 Idempotency-Key")
        version = await self._get_published_version(workflow)
        nodes = WorkflowRuntime.validate_definition(version.definition)
        execution_id = uuid.uuid4()
        execution = WorkflowExecution(id=execution_id, tenant_id=workflow.tenant_id, workflow_id=workflow.id,
                                       workflow_version_id=version.id, created_by=actor_id, idempotency_key=idempotency_key,
                                       status="pending", input_data=input_data)
        stmt = (pg_insert(WorkflowExecution).values(id=execution_id, tenant_id=execution.tenant_id,
            workflow_id=execution.workflow_id, workflow_version_id=execution.workflow_version_id,
            created_by=execution.created_by, idempotency_key=execution.idempotency_key, status=execution.status,
            input_data=execution.input_data).on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
            .returning(WorkflowExecution.id))
        claimed_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if claimed_id is None:
            existing = await self.find_execution_by_idempotency_key(workflow.tenant_id, idempotency_key)
            if existing is None:
                raise HTTPException(409, "Scheduled Trigger Idempotency claim 未收敛")
            return (existing, False) if return_created else existing
        execution = (await self.db.execute(select(WorkflowExecution).where(WorkflowExecution.id == claimed_id))).scalar_one()
        frontier_identity = WorkflowFrontierIdentity(
            execution_id=execution.id,
            workflow_version_id=version.id,
            decision_fingerprint=sha256(idempotency_key.encode("utf-8")).hexdigest(),
            node_ids=tuple(node["id"] for node in nodes),
        )
        await enqueue_frontier(self.db, tenant_id=execution.tenant_id, identity=frontier_identity,
                               node_ids=frontier_identity.node_ids, now=execution.created_at)
        audit_action = "workflow.trigger.scheduled_recovery" if recovery else "workflow.trigger.scheduled"
        trace_event = "trigger.scheduled.recovery" if recovery else "trigger.scheduled"
        await self.governance.audit(execution, actor_id, audit_action, "success", metadata={
            "trigger_id": str(trigger.id), "trigger_type": trigger.trigger_type, "timezone": config["timezone"],
            "interval_seconds": config["interval_seconds"], "idempotency_key": idempotency_key, "recovery": recovery,
            "dispatch_mode": "durable_frontier",
        })
        await self.governance.trace(execution, actor_id, trace_event, "pending", data={
            "trigger_id": str(trigger.id), "trigger_type": trigger.trigger_type, "timezone": config["timezone"],
            "interval_seconds": config["interval_seconds"], "recovery": recovery, "dispatch_mode": "durable_frontier",
        })
        await RuntimeIntegrationEventPublisher(self.db).publish(
            tenant_id=execution.tenant_id, event_type="scheduler.trigger.dispatched",
            source=RuntimeIntegrationEventPublisher.SOURCE_SCHEDULER, subject=str(execution.id),
            idempotency_key=f"scheduler-trigger:{trigger.id}:{idempotency_key}",
            payload={"trigger_id": str(trigger.id), "workflow_id": str(workflow.id),
                     "workflow_version_id": str(version.id), "execution_id": str(execution.id),
                     "scheduled_slot": input_data.get("scheduled_slot"), "planned_at": input_data.get("planned_at"),
                     "recovery": recovery, "dispatch_mode": "durable_frontier"},
        )
        await self.db.commit()
        return (execution, True) if return_created else execution

    async def invoke(self, workflow: Workflow, trigger: WorkflowTrigger, actor_id: UUID, input_data: dict,
                     idempotency_key: str | None = None, is_admin: bool = False, *, commit: bool = True) -> WorkflowExecution:
        """执行 Manual Trigger；调用方可选择在 Runtime 启动前统一提交 Execution、审计与幂等事实。"""
        if trigger.status != "enabled":
            raise HTTPException(409, "Trigger 已禁用")
        if trigger.trigger_type != "manual":
            raise HTTPException(409, "当前 Trigger 类型不可直接调用")
        version = await self._get_published_version(workflow)
        if idempotency_key:
            existing = await self.find_execution_by_idempotency_key(workflow.tenant_id, idempotency_key)
            if existing is not None:
                if existing.workflow_id != workflow.id:
                    raise HTTPException(409, "Idempotency-Key 已用于其他 Workflow Execution")
                return existing
        execution_service = WorkflowExecutionService(self.db)
        execution = await execution_service.create(
            workflow, version, actor_id, input_data, idempotency_key=idempotency_key, commit=False
        )
        await self.governance.audit(execution, actor_id, "workflow.trigger.invoked", "success", metadata={
            "trigger_id": str(trigger.id), "trigger_type": trigger.trigger_type})
        await self.governance.trace(execution, actor_id, "trigger.invoked", "pending", data={
            "trigger_id": str(trigger.id), "trigger_type": trigger.trigger_type})
        if commit:
            await self.db.commit()
        return await execution_service.run(execution, version, actor_id, is_admin)
