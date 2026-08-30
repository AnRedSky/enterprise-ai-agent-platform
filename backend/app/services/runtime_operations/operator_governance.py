"""Runtime Operator Action 治理服务。

职责：统一描述 Runtime / Workflow / Trigger 运维操作的可用性、确认、幂等边界，并把实际执行委托给现有领域服务。
边界：不实现 Workflow Execution 或 Trigger 状态机；不直接修改 Execution / Trigger 状态。
关键依赖：WorkflowExecutionService、WorkflowTriggerService、WorkflowRegistry 与 AuditLog。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
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
        "resume": {"pending", "running", "failed", "cancelled"},
    }

    @classmethod
    def definition(cls, resource_type: str, action: str) -> OperatorActionDefinition:
        """返回操作治理定义，并拒绝未注册的操作。

        Args:
            resource_type: 资源类型。
            action: 运维动作名称。
        Returns:
            对应的不可变操作治理定义。
        Raises:
            HTTPException: 资源类型或动作未注册时返回 404。
        """
        definition = cls._DEFINITIONS.get((resource_type, action))
        if definition is None:
            raise HTTPException(status_code=404, detail="Operator Action 不存在")
        return definition

    @classmethod
    def availability(cls, resource_type: str, action: str, status: str, *, trigger_type: str | None = None) -> dict[str, Any]:
        """根据后端当前资源事实计算操作可用性；不修改任何业务状态。

        Args:
            resource_type: 资源类型。
            action: 运维动作名称。
            status: 当前资源状态。
            trigger_type: Trigger 类型，仅 workflow_trigger 需要。
        Returns:
            前端可直接消费的操作治理 Contract。
        """
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
        """校验高风险确认与需要幂等键的操作请求。

        Args:
            resource_type: 资源类型。
            action: 运维动作名称。
            confirm: 调用方是否明确确认高风险动作。
            idempotency_key: 操作幂等键。
        Returns:
            通过校验的操作定义。
        Raises:
            HTTPException: 缺少确认或幂等键时返回 400。
        """
        definition = cls.definition(resource_type, action)
        if definition.requires_confirmation and not confirm:
            raise HTTPException(status_code=400, detail="高风险 Operator Action 必须明确 confirm=true")
        if definition.requires_idempotency_key and not idempotency_key:
            raise HTTPException(status_code=400, detail="当前 Operator Action 必须提供 Idempotency-Key")
        return definition

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _audit(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: UUID,
        action: str,
        status: str,
        workflow_id: UUID | None = None,
        workflow_version_id: UUID | None = None,
        workflow_execution_id: UUID | None = None,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """写入 Operator Action 审计事实；调用方负责事务提交。"""
        self.db.add(AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
            workflow_execution_id=workflow_execution_id,
            action=f"operator.{resource_type}.{action}",
            resource_type=resource_type,
            resource_id=str(resource_id),
            trace_id=str(workflow_execution_id or resource_id),
            status=status,
            error_code=error_code,
            metadata_json=metadata,
        ))
        await self.db.flush()

    async def _execution(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> WorkflowExecution:
        """通过正式 Workflow Execution Service 获取租户内资源。"""
        return await WorkflowExecutionService(self.db).get(execution_id, tenant_id, actor_id, is_admin)

    async def _trigger(self, trigger_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> tuple[Workflow, WorkflowTrigger]:
        """通过正式 Workflow Registry / Trigger Service 获取租户内 Trigger。"""
        trigger = (await self.db.execute(select(WorkflowTrigger).where(
            WorkflowTrigger.id == trigger_id,
            WorkflowTrigger.tenant_id == tenant_id,
        ))).scalar_one_or_none()
        if trigger is None:
            raise HTTPException(status_code=404, detail="Workflow Trigger 不存在")
        workflow = await WorkflowRegistry(self.db).get(trigger.workflow_id, tenant_id, actor_id, is_admin)
        return workflow, trigger

    async def execution_availability(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> dict[str, Any]:
        """返回 Workflow Execution 的全部 Operator Action 可用性。"""
        execution = await self._execution(execution_id, tenant_id, actor_id, is_admin)
        return {
            "resource_type": "workflow_execution",
            "resource_id": execution.id,
            "status": execution.status,
            "actions": [self.availability("workflow_execution", action, execution.status) for action in ("run", "cancel", "retry", "resume")],
        }

    async def trigger_availability(self, trigger_id: UUID, tenant_id: UUID, actor_id: UUID, is_admin: bool) -> dict[str, Any]:
        """返回 Workflow Trigger 的全部 Operator Action 可用性。"""
        _, trigger = await self._trigger(trigger_id, tenant_id, actor_id, is_admin)
        return {
            "resource_type": "workflow_trigger",
            "resource_id": trigger.id,
            "status": trigger.status,
            "trigger_type": trigger.trigger_type,
            "actions": [self.availability("workflow_trigger", action, trigger.status, trigger_type=trigger.trigger_type)
                        for action in ("enable", "disable", "delete", "invoke")],
        }

    async def execute_execution(
        self,
        execution_id: UUID,
        tenant_id: UUID,
        actor_id: UUID,
        is_admin: bool,
        action: str,
        *,
        confirm: bool = False,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowExecution:
        """执行 Workflow Execution 运维动作，并委托给现有 Execution 领域服务。

        Args:
            execution_id: 目标 Execution 标识。
            tenant_id: 身份上下文中的租户标识。
            actor_id: 当前操作人。
            is_admin: 是否允许跨用户访问本租户 Execution。
            action: run/cancel/retry/resume。
            confirm: 高风险动作确认。
            reason: Cancel 原因。
            idempotency_key: Retry 的唯一幂等键。
        Returns:
            原操作或新创建的 Workflow Execution。
        """
        self.validate_request("workflow_execution", action, confirm=confirm, idempotency_key=idempotency_key)
        service = WorkflowExecutionService(self.db)
        execution = await self._execution(execution_id, tenant_id, actor_id, is_admin)
        available = self.availability("workflow_execution", action, execution.status)
        if not available["allowed"]:
            raise HTTPException(status_code=409, detail="当前 Workflow Execution 状态不允许执行该 Operator Action")
        try:
            if action == "run":
                version = (await self.db.execute(
                    select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id)
                )).scalar_one_or_none()
                if version is None:
                    raise HTTPException(status_code=409, detail="Workflow Execution 版本不存在")
                result = await service.run(execution, version, actor_id, is_admin)
            elif action == "cancel":
                result = await service.cancel(execution, actor_id, reason)
            elif action == "retry":
                result = await service.retry(execution, actor_id)
            else:
                result = await service.resume_from_latest_checkpoint(execution, actor_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Operator Action 执行失败") from exc
        await self._audit(
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="workflow_execution",
            resource_id=execution_id,
            action=action,
            status="success",
            workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id,
            workflow_execution_id=execution_id,
            metadata={"idempotency_key_present": idempotency_key is not None, "confirmed": confirm},
        )
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def execute_trigger(
        self,
        trigger_id: UUID,
        tenant_id: UUID,
        actor_id: UUID,
        is_admin: bool,
        action: str,
        *,
        confirm: bool = False,
        input_data: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowTrigger | WorkflowExecution:
        """执行 Trigger 运维动作，并委托给现有 Trigger 领域服务。

        Args:
            trigger_id: 目标 Trigger 标识。
            tenant_id: 身份上下文中的租户标识。
            actor_id: 当前操作人。
            is_admin: 是否允许访问本租户其他用户拥有的 Workflow。
            action: enable/disable/delete/invoke。
            confirm: 高风险动作确认。
            input_data: Invoke 输入。
            idempotency_key: Invoke 唯一幂等键。
        Returns:
            更新后的 Trigger 或由 Invoke 创建的 Workflow Execution。
        """
        self.validate_request("workflow_trigger", action, confirm=confirm, idempotency_key=idempotency_key)
        workflow, trigger = await self._trigger(trigger_id, tenant_id, actor_id, is_admin)
        available = self.availability("workflow_trigger", action, trigger.status, trigger_type=trigger.trigger_type)
        if not available["allowed"]:
            raise HTTPException(status_code=409, detail="当前 Workflow Trigger 状态不允许执行该 Operator Action")
        service = WorkflowTriggerService(self.db)
        if action == "enable":
            result = await service.update(trigger, None, "enabled", None)
        elif action == "disable":
            result = await service.update(trigger, None, "disabled", None)
        elif action == "delete":
            await service.delete(trigger)
            result = trigger
        else:
            result = await service.invoke(workflow, trigger, actor_id, input_data or {}, idempotency_key=idempotency_key, is_admin=is_admin)
        await self._audit(
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="workflow_trigger",
            resource_id=trigger_id,
            action=action,
            status="success",
            workflow_id=workflow.id,
            workflow_execution_id=result.id if isinstance(result, WorkflowExecution) else None,
            metadata={"confirmed": confirm, "idempotency_key_present": idempotency_key is not None},
        )
        await self.db.commit()
        if isinstance(result, WorkflowExecution):
            await self.db.refresh(result)
        return result
