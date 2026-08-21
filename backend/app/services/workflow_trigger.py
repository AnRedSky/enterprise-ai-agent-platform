from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trigger import WorkflowTrigger
from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow_execution import WorkflowExecutionService
from app.services.workflow_governance import WorkflowGovernanceService
from app.services.workflow_trigger_schedule import validate_trigger_config


class WorkflowTriggerService:
    ALLOWED_TYPES = {"manual", "scheduled"}
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
            raise HTTPException(422, "Trigger type 必须为 manual 或 scheduled")
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
            await self.db.commit()
        except Exception as exc:
            from sqlalchemy.exc import IntegrityError
            if isinstance(exc, IntegrityError):
                await self.db.rollback()
                raise HTTPException(409, "同一 Workflow 下 Trigger name 已存在") from exc
            raise
        await self.db.refresh(trigger)
        return trigger

    async def update(self, trigger: WorkflowTrigger, name: str | None, status: str | None, config: dict | None) -> WorkflowTrigger:
        if name is not None:
            name = name.strip()
            if not name:
                raise HTTPException(422, "Trigger name 不能为空")
            trigger.name = name
        if status is not None:
            trigger.status = self.validate_status(status)
        if config is not None:
            config = self.validate_config(trigger.trigger_type, config)
            trigger.config = config
        try:
            await self.db.commit()
        except Exception as exc:
            from sqlalchemy.exc import IntegrityError
            if isinstance(exc, IntegrityError):
                await self.db.rollback()
                raise HTTPException(409, "同一 Workflow 下 Trigger name 已存在") from exc
            raise
        await self.db.refresh(trigger)
        return trigger

    async def delete(self, trigger: WorkflowTrigger) -> None:
        await self.db.delete(trigger)
        await self.db.commit()

    async def _get_published_version(self, workflow: Workflow) -> WorkflowVersion:
        if workflow.status != "published" or workflow.published_version_id is None:
            raise HTTPException(409, "Trigger 只能调用已发布 Workflow")
        version = (
            await self.db.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.id == workflow.published_version_id,
                    WorkflowVersion.workflow_id == workflow.id,
                )
            )
        ).scalar_one_or_none()
        if version is None or version.status != "published":
            raise HTTPException(409, "Workflow Published Version 不可用")
        return version

    async def invoke_scheduled(
        self,
        workflow: Workflow,
        trigger: WorkflowTrigger,
        actor_id: UUID,
        input_data: dict,
        idempotency_key: str,
        recovery: bool = False,
        return_created: bool = False,
    ) -> WorkflowExecution | tuple[WorkflowExecution, bool]:
        """Dispatch a scheduled Trigger with a transaction-serialized PostgreSQL idempotency claim."""
        if trigger.status != "enabled":
            raise HTTPException(409, "Trigger 已禁用")
        if trigger.trigger_type != "scheduled":
            raise HTTPException(409, "当前 Trigger 类型不是 scheduled")
        config = self.validate_config(trigger.trigger_type, trigger.config or {})
        if not idempotency_key:
            raise HTTPException(422, "Scheduled Trigger 必须提供调度 Idempotency-Key")
        version = await self._get_published_version(workflow)
        WorkflowRuntime.validate_definition(version.definition)

        # Serialize the check + claim for the same slot at the PostgreSQL
        # transaction boundary. The unique constraint remains the final
        # persistence safety net, while the advisory lock makes the scheduler
        # convergence deterministic for concurrent workers.
        await self.db.execute(select(func.pg_advisory_xact_lock(func.hashtext(idempotency_key))))

        existing = await self.find_execution_by_idempotency_key(workflow.tenant_id, idempotency_key)
        if existing is not None:
            result: WorkflowExecution | tuple[WorkflowExecution, bool] = (existing, False) if return_created else existing
            return result

        execution_id = uuid.uuid4()
        execution = WorkflowExecution(
            id=execution_id,
            tenant_id=workflow.tenant_id,
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            created_by=actor_id,
            idempotency_key=idempotency_key,
            status="pending",
            input_data=input_data,
        )
        stmt = (
            pg_insert(WorkflowExecution)
            .values(
                id=execution_id,
                tenant_id=execution.tenant_id,
                workflow_id=execution.workflow_id,
                workflow_version_id=execution.workflow_version_id,
                created_by=execution.created_by,
                idempotency_key=execution.idempotency_key,
                status=execution.status,
                input_data=execution.input_data,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
            .returning(WorkflowExecution.id)
        )
        claimed_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if claimed_id is None:
            existing = await self.find_execution_by_idempotency_key(workflow.tenant_id, idempotency_key)
            if existing is None:
                raise HTTPException(409, "Scheduled Trigger Idempotency claim 未收敛")
            return (existing, False) if return_created else existing

        execution = (await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == claimed_id)
        )).scalar_one()
        audit_action = "workflow.trigger.scheduled_recovery" if recovery else "workflow.trigger.scheduled"
        trace_event = "trigger.scheduled.recovery" if recovery else "trigger.scheduled"
        await self.governance.audit(
            execution,
            actor_id,
            audit_action,
            "success",
            metadata={
                "trigger_id": str(trigger.id),
                "trigger_type": trigger.trigger_type,
                "timezone": config["timezone"],
                "interval_seconds": config["interval_seconds"],
                "idempotency_key": idempotency_key,
                "recovery": recovery,
            },
        )
        await self.governance.trace(
            execution,
            actor_id,
            trace_event,
            "pending",
            data={
                "trigger_id": str(trigger.id),
                "trigger_type": trigger.trigger_type,
                "timezone": config["timezone"],
                "interval_seconds": config["interval_seconds"],
                "recovery": recovery,
            },
        )
        await self.db.commit()
        result_execution = await WorkflowExecutionService(self.db).run(execution, version, actor_id)
        return (result_execution, True) if return_created else result_execution

    async def invoke(self, workflow: Workflow, trigger: WorkflowTrigger, actor_id: UUID,
                     input_data: dict, idempotency_key: str | None = None, is_admin: bool = False) -> WorkflowExecution:
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
        execution = await execution_service.create(workflow, version, actor_id, input_data, idempotency_key=idempotency_key)
        await self.governance.audit(
            execution,
            actor_id,
            "workflow.trigger.invoked",
            "success",
            metadata={"trigger_id": str(trigger.id), "trigger_type": trigger.trigger_type},
        )
        await self.governance.trace(execution, actor_id, "trigger.invoked", "pending", data={
            "trigger_id": str(trigger.id), "trigger_type": trigger.trigger_type,
        })
        await self.db.commit()
        return await execution_service.run(execution, version, actor_id, is_admin)
