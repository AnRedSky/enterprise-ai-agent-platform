from __future__ import annotations

import hashlib
import uuid
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trigger import WorkflowTrigger
from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow import WorkflowExecutionService, WorkflowGovernanceService
from app.services.workflow_trigger import WorkflowTriggerService
from app.services.workflow_trigger_schedule import verify_webhook_secret


class WebhookTriggerService:
    """Webhook 事件入口服务，负责认证、幂等声明与 Workflow 执行触发。

    边界：不重复实现 Workflow Execution、Governance 或 Registry，统一复用 Workflow 领域正式入口。
    关键依赖：WorkflowRuntime、WorkflowTriggerService 与 services.workflow。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.governance = WorkflowGovernanceService(db)

    async def get_trigger(self, trigger_id: UUID) -> WorkflowTrigger:
        trigger = (
            await self.db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger_id))
        ).scalar_one_or_none()
        if trigger is None:
            raise HTTPException(404, "Webhook Trigger 不存在")
        if trigger.trigger_type != "webhook":
            raise HTTPException(404, "Webhook Trigger 不存在")
        return trigger

    @staticmethod
    def authenticate(trigger: WorkflowTrigger, supplied_secret: str | None) -> None:
        if trigger.status != "enabled":
            raise HTTPException(409, "Webhook Trigger 已禁用")
        if not verify_webhook_secret(trigger.config or {}, supplied_secret):
            raise HTTPException(401, "Webhook secret 无效")

    @staticmethod
    def event_identity(trigger: WorkflowTrigger, payload: dict, idempotency_key: str | None) -> str:
        if idempotency_key:
            identity = idempotency_key.strip()
        else:
            field = str((trigger.config or {}).get("event_id_field", "event_id"))
            value = payload.get(field)
            identity = str(value).strip() if value is not None else ""
        if not identity:
            raise HTTPException(422, "Webhook 必须提供 Idempotency-Key 或配置字段中的 event_id")
        if len(identity) > 100:
            raise HTTPException(422, "Webhook event identity 最长 100 个字符")
        return identity

    @staticmethod
    def durable_idempotency_key(trigger_id: UUID, identity: str) -> str:
        """返回稳定的公开幂等键；超长时使用确定性摘要控制长度。"""
        public_key = f"webhook:{trigger_id}:{identity}"
        if len(public_key) <= 100:
            return public_key
        digest = hashlib.sha256(f"{trigger_id}:{identity}".encode("utf-8")).hexdigest()
        return f"webhook:{digest}"

    async def _published_version(self, trigger: WorkflowTrigger) -> tuple[WorkflowVersion, WorkflowTrigger]:
        workflow = (
            await self.db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger.id))
        ).scalar_one()
        version = await WorkflowTriggerService(self.db)._get_published_version(
            await self.db.get(Workflow, trigger.workflow_id)
        )
        return version, workflow

    async def invoke(
        self,
        trigger: WorkflowTrigger,
        payload: dict,
        supplied_secret: str | None,
        idempotency_key: str | None,
        request_id: str,
    ) -> tuple[WorkflowExecution, bool, str]:
        self.authenticate(trigger, supplied_secret)
        identity = self.event_identity(trigger, payload, idempotency_key)
        durable_key = self.durable_idempotency_key(trigger.id, identity)

        workflow = await self.db.get(Workflow, trigger.workflow_id)
        if workflow is None or workflow.tenant_id != trigger.tenant_id:
            raise HTTPException(404, "Webhook Workflow 不存在")
        trigger_service = WorkflowTriggerService(self.db)
        version = await trigger_service._get_published_version(workflow)
        WorkflowRuntime.validate_definition(version.definition)

        execution_id = uuid.uuid4()
        stmt = (
            pg_insert(WorkflowExecution)
            .values(
                id=execution_id,
                tenant_id=trigger.tenant_id,
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                created_by=trigger.created_by,
                idempotency_key=durable_key,
                status="pending",
                input_data=payload,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
            .returning(WorkflowExecution.id)
        )
        claimed_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if claimed_id is None:
            existing = await trigger_service.find_execution_by_idempotency_key(trigger.tenant_id, durable_key)
            if existing is None:
                raise HTTPException(409, "Webhook Idempotency claim 未收敛")
            return existing, False, identity

        execution = (await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == claimed_id)
        )).scalar_one()
        await self.governance.audit(
            execution,
            trigger.created_by,
            "workflow.trigger.webhook",
            "success",
            metadata={
                "trigger_id": str(trigger.id),
                "trigger_type": "webhook",
                "request_id": request_id,
                "event_identity": identity,
            },
        )
        await self.governance.trace(
            execution,
            trigger.created_by,
            "trigger.webhook",
            "pending",
            data={"trigger_id": str(trigger.id), "trigger_type": "webhook", "request_id": request_id},
        )
        await self.db.commit()
        result = await WorkflowExecutionService(self.db).run(execution, version, trigger.created_by)
        return result, True, identity
