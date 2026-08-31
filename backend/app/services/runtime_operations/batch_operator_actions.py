"""Runtime 批量 Operator Action 治理服务。

职责：将多个同类型 Runtime Operator Action 编排为一次 tenant-scoped 批量请求，并逐项委托现有 OperatorActionGovernanceService。
边界：不实现 Workflow Execution、Workflow Trigger 状态机，不直接修改 Durable Fact；批量层只负责输入约束、逐项结果与批次级幂等键派生。
关键依赖：OperatorActionGovernanceService、SQLAlchemy AsyncSession 与 UUID。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


@dataclass(frozen=True)
class BatchOperatorActionItem:
    """描述单个批量动作的结果。"""

    resource_id: UUID
    status: str
    result: Any = None
    error_code: str | None = None
    detail: str | None = None


class BatchOperatorActionService:
    """统一编排批量 Operator Action，并复用单项 Operator Action 生命周期。"""

    MAX_ITEMS = 100

    def __init__(self, db: AsyncSession):
        self.db = db
        self.operator = OperatorActionGovernanceService(db)

    @classmethod
    def validate_request(
        cls,
        resource_type: str,
        action: str,
        resource_ids: list[UUID],
        *,
        confirm: bool,
        idempotency_key: str | None,
    ) -> None:
        """校验批量请求的资源类型、动作、数量、确认与幂等边界。"""
        if resource_type not in {"workflow_execution", "workflow_trigger"}:
            raise HTTPException(status_code=400, detail="不支持的批量 Operator Action resource_type")
        if not resource_ids or len(resource_ids) > cls.MAX_ITEMS:
            raise HTTPException(status_code=422, detail="resource_ids 必须包含 1 到 100 个项目")
        if len(set(resource_ids)) != len(resource_ids):
            raise HTTPException(status_code=422, detail="resource_ids 不允许重复")
        definition = OperatorActionGovernanceService.validate_request(
            resource_type,
            action,
            confirm=confirm,
            idempotency_key=idempotency_key,
        )
        if not definition.idempotent:
            raise HTTPException(status_code=409, detail="当前 Operator Action 不支持批量执行")

    @staticmethod
    def _item_idempotency_key(batch_key: str, resource_type: str, action: str, resource_id: UUID) -> str:
        """从批次幂等键稳定派生单项键，保证批量 Retry/Invoke 重试不会重复创建生命周期事实。"""
        payload = f"{batch_key}|{resource_type}|{action}|{resource_id}".encode("utf-8")
        return f"batch-{hashlib.sha256(payload).hexdigest()}"

    async def execute(
        self,
        *,
        resource_type: str,
        action: str,
        resource_ids: list[UUID],
        tenant_id: UUID,
        actor_id: UUID,
        is_admin: bool,
        confirm: bool = False,
        reason: str | None = None,
        input_data: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """逐项执行批量动作并返回成功、拒绝与失败结果；每项继续走正式 Operator Action 领域入口。"""
        self.validate_request(
            resource_type,
            action,
            resource_ids,
            confirm=confirm,
            idempotency_key=idempotency_key,
        )

        items: list[BatchOperatorActionItem] = []
        for resource_id in resource_ids:
            item_key = (
                self._item_idempotency_key(idempotency_key, resource_type, action, resource_id)
                if idempotency_key and OperatorActionGovernanceService.definition(resource_type, action).requires_idempotency_key
                else None
            )
            try:
                if resource_type == "workflow_execution":
                    result = await self.operator.execute_execution(
                        resource_id,
                        tenant_id,
                        actor_id,
                        is_admin,
                        action,
                        confirm=confirm,
                        reason=reason,
                        idempotency_key=item_key,
                    )
                else:
                    result = await self.operator.execute_trigger(
                        resource_id,
                        tenant_id,
                        actor_id,
                        is_admin,
                        action,
                        confirm=confirm,
                        input_data=input_data,
                        idempotency_key=item_key,
                    )
            except HTTPException as exc:
                await self.db.rollback()
                items.append(BatchOperatorActionItem(
                    resource_id=resource_id,
                    status="rejected",
                    error_code=f"HTTP_{exc.status_code}",
                    detail=str(exc.detail),
                ))
                continue
            except Exception:
                await self.db.rollback()
                items.append(BatchOperatorActionItem(
                    resource_id=resource_id,
                    status="failed",
                    error_code="BATCH_OPERATOR_ACTION_FAILED",
                    detail="批量 Operator Action 执行失败",
                ))
                continue
            items.append(BatchOperatorActionItem(resource_id=resource_id, status="succeeded", result=result))

        succeeded = [item for item in items if item.status == "succeeded"]
        rejected = [item for item in items if item.status == "rejected"]
        failed = [item for item in items if item.status == "failed"]
        return {
            "resource_type": resource_type,
            "action": action,
            "total": len(items),
            "succeeded_count": len(succeeded),
            "rejected_count": len(rejected),
            "failed_count": len(failed),
            "items": items,
        }
