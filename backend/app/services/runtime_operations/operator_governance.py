"""Runtime Operator Action 治理服务。

职责：统一描述 Runtime / Workflow / Trigger 运维操作的可用性、确认、幂等边界，并把实际执行委托给现有领域服务。
边界：不实现 Workflow Execution 或 Trigger 状态机；不直接修改 Execution / Trigger 状态。
关键依赖：WorkflowExecutionService、WorkflowTriggerService、WorkflowRegistry、AuditLog 与 OperatorActionIdempotency。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trigger import WorkflowTrigger
from app.services.trigger import WorkflowTriggerService
from app.services.workflow import WorkflowExecutionService, WorkflowRegistry


@dataclass(frozen=True)
class OperatorActionDefinition:
    """描述单个运维操作的治理属性。"""

    action: str
    resource_type: str
    requires_confirmation: bool
    requires_idempotency_key: bool
    idempotent: bool
    description: str


class OperatorActionGovernanceService:
    """统一治理运维操作，并复用现有 Workflow / Trigger 领域生命周期。"""

    _DEFINITIONS: dict[tuple[str, str], OperatorActionDefinition] = {
        ("workflow_execution", "run"): OperatorActionDefinition("run", "workflow_execution", False, False, True, "执行 pending Workflow Execution"),
        ("workflow_execution", "cancel"): OperatorActionDefinition("cancel", "workflow_execution", True, False, True, "取消 pending 或 running Workflow Execution"),
        ("workflow_execution", "retry"): OperatorActionDefinition("retry", "workflow_execution", True, True, True, "为 failed Workflow Execution 创建唯一 Retry Execution"),
        ("workflow_execution", "resume"): OperatorActionDefinition("resume", "workflow_execution", True, False, True, "基于最新 Durable Checkpoint 创建 Resume Execution"),
        ("workflow_trigger", "enable"): OperatorActionDefinition("enable", "workflow_trigger", True, False, True, "启用 Workflow Trigger"),
        ("workflow_trigger", "disable"): OperatorActionDefinition("disable", "workflow_trigger", True, False, True, "禁用 Workflow Trigger"),
        ("workflow_trigger", "delete"): OperatorActionDefinition("delete", "workflow_trigger", True, False, True, "删除 Workflow Trigger"),
        ("workflow_trigger", "invoke"): OperatorActionDefinition("invoke", "workflow_trigger", False, True, True, "调用 manual Workflow Trigger"),
    }

    _EXECUTION_STATES: dict[str, set[str]] = {
        "run": {"pending"},
        "cancel": {"pending", "running"},
        "retry": {"failed"},
        "resume": {"failed"},
    }

    @classmethod
    def definition(cls, resource_type: str, action: str) -> OperatorActionDefinition:
        """返回操作治理定义，并拒绝未注册的操作。"""
        definition = cls._DEFINITIONS.get((resource_type, action))
        if definition is None:
            raise HTTPException(status_code=404, detail="Operator Action 不存在")
        return definition

    @classmethod
    def availability(cls, resource_type: str, action: str, status: str, *, trigger_type: str | None = None) -> dict[str, Any]:
        """根据后端当前资源事实计算操作可用性；不修改任何业务状态。"""
        definition = cls.definition(resource_type, action)
        allowed = False
        reason_code = "ACTION_NOT_ALLOWED"
        if resource_type == "workflow_execution":
            allowed = status in cls._EXECUTION_STATES[action]
            reason_code = "AVAILABLE" if allowed else "INVALID_EXECUTION_STATE"
        elif resource_type == "workflow_trigger":
            if action == "enable":
                allowed = status == "disabled"
            elif action == "disable":
                allowed = status == "enabled"
            elif action == "delete":
                allowed = status in {"enabled", "disabled"}
            elif action == "invoke":
                allowed = status == "enabled" and trigger_type == "manual"
                if trigger_type != "manual":
                    reason_code = "TRIGGER_TYPE_NOT_INVOKABLE"
            if allowed:
                reason_code = "AVAILABLE"
        return {
            "resource_type": resource_type,
            "action": action,
            "allowed": allowed,
            "reason_code": reason_code,
            "requires_confirmation": definition.requires_confirmation,
            "requires_idempotency_key": definition.requires_idempotency_key,
            "idempotent": definition.idempotent,
            "description": definition.description,
        }

    @classmethod
    def validate_request(cls, resource_type: str, action: str, *, confirm: bool, idempotency_key: str | None) -> OperatorActionDefinition:
        """校验高风险确认与需要幂等键的操作请求。"""
        definition = cls.definition(resource_type, action)
        if definition.requires_confirmation and not confirm:
            raise HTTPException(status_code=400, detail="高风险 Operator Action 必须明确 confirm=true")
        if definition.requires_idempotency_key and not idempotency_key:
            raise HTTPException(status_code=400, detail="当前 Operator Action 必须提供 Idempotency-Key")
        return definition

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _ensure_operator_action(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: UUID,
        action: str,
        result_resource_type: str,
        result_resource_id: UUID,
        idempotency_key: str | None,
        status: str,
        error_code: str | None = None,
    ) -> OperatorActionIdempotency:
        """确保每个已执行 Operator Action 都拥有可追踪的持久事实。

        Args:
            actor_id: 发起运维操作的用户。
            tenant_id: 当前租户边界。
            resource_type: 操作目标资源类型。
            resource_id: 操作目标资源标识。
            action: 操作名称。
            result_resource_type: 最终结果资源类型。
            result_resource_id: 最终结果资源标识。
            idempotency_key: 客户端幂等键；非幂等入口使用内部唯一键。
            status: Operator Action 最终状态。
            error_code: 失败时的结构化错误码。

        Returns:
            已存在或新建的 Operator Action 持久事实。
        """
        if idempotency_key:
            record = (await self.db.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == idempotency_key,
            ))).scalar_one_or_none()
            if record is None:
                raise HTTPException(status_code=409, detail="Operator Action 幂等事实不存在")
        else:
            record = OperatorActionIdempotency(
                tenant_id=tenant_id,
                actor_id=actor_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                idempotency_key=f"internal:{uuid4()}",
                status=status,
            )
            self.db.add(record)
            await self.db.flush()
        record.status = status
        record.result_resource_type = result_resource_type if status == "succeeded" else None
        record.result_resource_id = result_resource_id if status == "succeeded" else None
        record.error_code = error_code
        await self.db.flush()
        return record

    async def _audit(self, *, actor_id: UUID, tenant_id: UUID, resource_type: str, resource_id: UUID,
                     action: str, status: str, workflow_id: UUID | None = None,
                     workflow_version_id: UUID | None = None, workflow_execution_id: UUID | None = None,
                     idempotency_key: str | None = None, error_code: str | None = None,
                     metadata: dict[str, Any] | None = None) -> None:
        """写入与 Operator Action 强关联的审计事实；调用方负责事务提交。"""
        result_resource_type = "workflow_execution" if workflow_execution_id is not None else resource_type
        result_resource_id = workflow_execution_id or resource_id
        operator_status = "succeeded" if status == "success" else status
        operator_action = await self._ensure_operator_action(
            actor_id=actor_id, tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id,
            action=action, result_resource_type=result_resource_type, result_resource_id=result_resource_id,
            idempotency_key=idempotency_key, status=operator_status, error_code=error_code,
        )
        self.db.add(AuditLog(
            actor_id=actor_id, tenant_id=tenant_id, workflow_id=workflow_id,
            workflow_version_id=workflow_version_id, workflow_execution_id=workflow_execution_id,
            operator_action_id=operator_action.id, action=f"operator.{resource_type}.{action}",
            resource_type=resource_type, resource_id=str(resource_id),
            trace_id=str(workflow_execution_id or resource_id), status=status,
            error_code=error_code, metadata_json=metadata,
        ))
        await self.db.flush()

    async def _claim_idempotency(self, *, tenant_id: UUID, actor_id: UUID, resource_type: str,
                                 resource_id: UUID, action: str, idempotency_key: str) -> OperatorActionIdempotency | None:
        """原子登记 Operator Action 幂等键，并返回已有结果记录。"""
        statement = pg_insert(OperatorActionIdempotency).values(
            tenant_id=tenant_id, actor_id=actor_id, resource_type=resource_type,
            resource_id=resource_id, action=action, idempotency_key=idempotency_key, status="started",
        ).on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
        inserted = (await self.db.execute(statement)).rowcount
        if inserted:
            return None
        existing = (await self.db.execute(select(OperatorActionIdempotency).where(
            OperatorActionIdempotency.tenant_id == tenant_id,
            OperatorActionIdempotency.idempotency_key == idempotency_key,
        ))).scalar_one_or_none()
        if existing is None:
            raise HTTPException(status_code=409, detail="Operator Action 幂等键未收敛")
        if existing.resource_type != resource_type or existing.resource_id != resource_id or existing.action != action:
            raise HTTPException(status_code=409, detail="Idempotency-Key 已用于其他 Operator Action")
        return existing

    async def _reuse_or_raise(self, record: OperatorActionIdempotency | None) -> WorkflowExecution | None:
        """处理已存在的幂等事实，避免重复执行同一可重试操作。"""
        if record is None:
            return None
        if record.status != "succeeded" or record.result_resource_id is None:
            raise HTTPException(status_code=409, detail="相同 Idempotency-Key 的 Operator Action 已在处理中或此前失败")
        if record.result_resource_type != "workflow_execution":
            raise HTTPException(status_code=409, detail="Operator Action 幂等结果不是 Workflow Execution")
        result = (await self.db.execute(select(WorkflowExecution).where(
            WorkflowExecution.tenant_id == record.tenant_id,
            WorkflowExecution.id == record.result_resource_id,
        ))).scalar_one_or_none()
        if result is None:
            raise HTTPException(status_code=409, detail="Operator Action 幂等结果已失效")
        return result

    async def _finish_idempotency(self, record_key: str | None, tenant_id: UUID, result_id: UUID | None,
                                  *, result_resource_type: str | None = None, status: str = "succeeded",
                                  error_code: str | None = None) -> None:
        """持久化幂等请求的最终结果；失败请求不得伪造结果资源。"""
        if record_key is None:
            return
        record = (await self.db.execute(select(OperatorActionIdempotency).where(
            OperatorActionIdempotency.tenant_id == tenant_id,
            OperatorActionIdempotency.idempotency_key == record_key,
        ))).scalar_one()
        record.status = status
        record.result_resource_id = result_id if status == "succeeded" else None
        record.result_resource_type = result_resource_type if status == "succeeded" else None
        record.error_code = error_code
        await self.db.flush()

    async def _execution(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> WorkflowExecution:
        """通过正式 Workflow Execution Service 获取租户内资源。"""
        return await WorkflowExecutionService(self.db).get(execution_id, tenant_id, actor_id, is_admin)

    async def _trigger(self, trigger_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> tuple[Workflow, WorkflowTrigger]:
        """通过正式 Workflow Registry / Trigger Service 获取租户内 Trigger。"""
        trigger = (await self.db.execute(select(WorkflowTrigger).where(
            WorkflowTrigger.id == trigger_id, WorkflowTrigger.tenant_id == tenant_id,
        ))).scalar_one_or_none()
        if trigger is None:
            raise HTTPException(status_code=404, detail="Workflow Trigger 不存在")
        workflow = await WorkflowRegistry(self.db).get(trigger.workflow_id, tenant_id, actor_id, is_admin)
        return workflow, trigger

    async def execution_availability(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> dict[str, Any]:
        """返回 Workflow Execution 的全部 Operator Action 可用性，并对 Resume 复用正式恢复评估。"""
        execution = await self._execution(execution_id, tenant_id, actor_id, is_admin)
        actions = [self.availability("workflow_execution", action, execution.status) for action in ("run", "cancel", "retry", "resume")]
        resume = next(item for item in actions if item["action"] == "resume")
        if execution.status == "failed":
            execution_service = WorkflowExecutionService(self.db)
            checkpoint = await execution_service.checkpoint.latest(execution.id)
            assessment = execution_service.checkpoint_recovery.assess(
                execution_id=execution.id, workflow_version_id=execution.workflow_version_id,
                execution_status=execution.status, worker_owner=execution.worker_owner, checkpoint=checkpoint,
            )
            resume["allowed"] = assessment.eligible
            resume["reason_code"] = "AVAILABLE" if assessment.eligible else assessment.reason_code.upper()
        return {"resource_type": "workflow_execution", "resource_id": execution.id,
                "status": execution.status, "actions": actions}

    async def trigger_availability(self, trigger_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> dict[str, Any]:
        """返回 Workflow Trigger 的全部 Operator Action 可用性。"""
        _, trigger = await self._trigger(trigger_id, tenant_id, actor_id, is_admin)
        return {
            "resource_type": "workflow_trigger", "resource_id": trigger.id, "status": trigger.status,
            "trigger_type": trigger.trigger_type,
            "actions": [self.availability("workflow_trigger", action, trigger.status, trigger_type=trigger.trigger_type)
                        for action in ("enable", "disable", "delete", "invoke")],
        }

    async def execute_execution(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool,
                                action: str, *, confirm: bool = False, reason: str | None = None,
                                idempotency_key: str | None = None) -> WorkflowExecution:
        """执行 Workflow Execution 运维动作，并委托给现有 Execution 领域服务。"""
        definition = self.validate_request("workflow_execution", action, confirm=confirm, idempotency_key=idempotency_key)
        execution = await self._execution(execution_id, tenant_id, actor_id, is_admin)
        available = self.availability("workflow_execution", action, execution.status)
        resume_checkpoint_sequence: int | None = None
        if action == "resume" and execution.status == "failed":
            execution_service = WorkflowExecutionService(self.db)
            checkpoint = await execution_service.checkpoint.latest(execution.id)
            assessment = execution_service.checkpoint_recovery.assess(
                execution_id=execution.id, workflow_version_id=execution.workflow_version_id,
                execution_status=execution.status, worker_owner=execution.worker_owner, checkpoint=checkpoint,
            )
            available["allowed"] = assessment.eligible
            if assessment.eligible:
                resume_checkpoint_sequence = assessment.checkpoint_sequence
        if not available["allowed"]:
            raise HTTPException(status_code=409, detail="当前 Workflow Execution 状态不允许执行该 Operator Action")

        effective_idempotency_key = idempotency_key
        if action == "resume":
            if resume_checkpoint_sequence is None:
                raise HTTPException(status_code=409, detail="Resume Candidate 缺少确定性 Checkpoint sequence")
            if effective_idempotency_key is None:
                effective_idempotency_key = f"internal:resume:{execution_id}:{resume_checkpoint_sequence}"

        idempotency_record = None
        if definition.requires_idempotency_key or action == "resume":
            idempotency_record = await self._claim_idempotency(
                tenant_id=tenant_id, actor_id=actor_id, resource_type="workflow_execution",
                resource_id=execution_id, action=action, idempotency_key=effective_idempotency_key or "",
            )
            reused = await self._reuse_or_raise(idempotency_record)
            if reused is not None:
                return reused
        service = WorkflowExecutionService(self.db)
        try:
            if action == "run":
                version = (await self.db.execute(select(WorkflowVersion).where(
                    WorkflowVersion.id == execution.workflow_version_id
                ))).scalar_one_or_none()
                if version is None:
                    raise HTTPException(status_code=409, detail="Workflow Execution 版本不存在")
                result = await service.run(execution, version, actor_id, is_admin)
            elif action == "cancel":
                result = await service.cancel(execution, actor_id, reason)
            elif action == "retry":
                result = await service.retry(execution, actor_id, commit=False)
            else:
                result = await service.resume_from_latest_checkpoint(execution, actor_id, commit=False)
        except HTTPException as exc:
            if idempotency_record is None and effective_idempotency_key is not None:
                await self._finish_idempotency(effective_idempotency_key, tenant_id, None, status="failed", error_code=f"HTTP_{exc.status_code}")
                await self.db.commit()
            raise
        except Exception as exc:
            if idempotency_record is None and effective_idempotency_key is not None:
                await self._finish_idempotency(effective_idempotency_key, tenant_id, None, status="failed", error_code="OPERATOR_ACTION_FAILED")
                await self.db.commit()
            raise HTTPException(status_code=500, detail="Operator Action 执行失败") from exc
        if effective_idempotency_key is not None:
            await self._finish_idempotency(effective_idempotency_key, tenant_id, result.id, result_resource_type="workflow_execution")
        await self._audit(
            actor_id=actor_id, tenant_id=tenant_id, resource_type="workflow_execution", resource_id=execution_id,
            action=action, status="success", workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id, workflow_execution_id=result.id,
            idempotency_key=effective_idempotency_key,
            metadata={"idempotency_key_present": idempotency_key is not None, "confirmed": confirm},
        )
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def execute_trigger(self, trigger_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool,
                              action: str, *, confirm: bool = False, input_data: dict[str, Any] | None = None,
                              idempotency_key: str | None = None) -> WorkflowTrigger | WorkflowExecution:
        """执行 Trigger 运维动作，并委托给现有 Trigger 领域服务。"""
        definition = self.validate_request("workflow_trigger", action, confirm=confirm, idempotency_key=idempotency_key)
        workflow, trigger = await self._trigger(trigger_id, tenant_id, actor_id, is_admin)
        available = self.availability("workflow_trigger", action, trigger.status, trigger_type=trigger.trigger_type)
        if not available["allowed"]:
            raise HTTPException(status_code=409, detail="当前 Workflow Trigger 状态不允许执行该 Operator Action")
        idempotency_record = None
        if definition.requires_idempotency_key:
            idempotency_record = await self._claim_idempotency(
                tenant_id=tenant_id, actor_id=actor_id, resource_type="workflow_trigger",
                resource_id=trigger_id, action=action, idempotency_key=idempotency_key or "",
            )
            reused = await self._reuse_or_raise(idempotency_record)
            if reused is not None:
                return reused
        service = WorkflowTriggerService(self.db)
        try:
            if action == "enable":
                result = await service.update(trigger, None, "enabled", None)
            elif action == "disable":
                result = await service.update(trigger, None, "disabled", None)
            elif action == "delete":
                await service.delete(trigger)
                result = trigger
            else:
                result = await service.invoke(
                    workflow, trigger, actor_id, input_data or {}, idempotency_key=idempotency_key, is_admin=is_admin,
                )
        except HTTPException as exc:
            if idempotency_record is None and definition.requires_idempotency_key:
                await self._finish_idempotency(idempotency_key, tenant_id, None, status="failed", error_code=f"HTTP_{exc.status_code}")
                await self.db.commit()
            raise
        except Exception as exc:
            if idempotency_record is None and definition.requires_idempotency_key:
                await self._finish_idempotency(idempotency_key, tenant_id, None, status="failed", error_code="OPERATOR_ACTION_FAILED")
                await self.db.commit()
            raise HTTPException(status_code=500, detail="Operator Action 执行失败") from exc
        if definition.requires_idempotency_key:
            if not isinstance(result, WorkflowExecution):
                raise HTTPException(status_code=500, detail="Operator Action 结果不是 Workflow Execution")
            await self._finish_idempotency(idempotency_key, tenant_id, result.id, result_resource_type="workflow_execution")
        await self._audit(
            actor_id=actor_id, tenant_id=tenant_id, resource_type="workflow_trigger", resource_id=trigger_id,
            action=action, status="success", workflow_id=workflow.id,
            workflow_execution_id=result.id if isinstance(result, WorkflowExecution) else None,
            idempotency_key=idempotency_key,
            metadata={"confirmed": confirm, "idempotency_key_present": idempotency_key is not None},
        )
        await self.db.commit()
        if isinstance(result, WorkflowExecution):
            await self.db.refresh(result)
        return result
