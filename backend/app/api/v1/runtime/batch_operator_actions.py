"""Runtime 批量 Operator Action HTTP 协议模块。

职责：暴露 tenant-scoped 批量 Workflow Execution / Trigger Operator Action 接口。
边界：只负责身份、租户上下文、请求协议与响应组装；实际生命周期继续委托 OperatorActionGovernanceService。
关键依赖：BatchOperatorActionService、FastAPI、SQLAlchemy AsyncSession 与认证依赖。
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims, require_roles
from app.dependencies.db import get_db
from app.services.runtime_operations.batch_operator_actions import BatchOperatorActionService


router = APIRouter(prefix="/api/v1/runtime/operator-actions", tags=["runtime-operator-actions"])


class BatchOperatorActionRequest(BaseModel):
    """批量 Operator Action 执行请求。"""

    resource_type: Literal["workflow_execution", "workflow_trigger"]
    action: str = Field(min_length=1, max_length=32)
    resource_ids: list[UUID] = Field(min_length=1, max_length=100)
    confirm: bool = False
    reason: str | None = Field(default=None, max_length=500)
    input_data: dict[str, Any] = Field(default_factory=dict)


class BatchOperatorActionItemResponse(BaseModel):
    """单个批量动作结果。"""

    resource_id: UUID
    status: Literal["succeeded", "rejected", "failed"]
    error_code: str | None = None
    detail: str | None = None
    result: Any = None


class BatchOperatorActionResponse(BaseModel):
    """批量 Operator Action 汇总响应。"""

    resource_type: str
    action: str
    total: int
    succeeded_count: int
    rejected_count: int
    failed_count: int
    items: list[BatchOperatorActionItemResponse]


def _claims(credentials=Depends(bearer)) -> dict:
    """解析当前身份上下文，不接受请求体提交 tenant_id。"""
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    """从已验证身份中取得租户标识。"""
    return UUID(claims["tenant_id"])


def _actor_id(claims: dict) -> UUID:
    """从已验证身份中取得操作人标识。"""
    return UUID(claims["sub"])


def _is_admin(claims: dict) -> bool:
    """判断当前身份是否具备本租户管理员权限。"""
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return "admin" in roles


def _serialize_result(result: Any) -> Any:
    """将领域对象转换为可序列化的最小资源结果，避免把数据库模型直接暴露给协议层。"""
    if result is None:
        return None
    if hasattr(result, "id") and hasattr(result, "status"):
        return {"id": result.id, "status": result.status}
    return result


@router.post("/batch", response_model=BatchOperatorActionResponse)
async def execute_batch_operator_action(
    request: BatchOperatorActionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    claims: dict = Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """执行 tenant-scoped 批量 Operator Action；不会创建第二套生命周期。"""
    service = BatchOperatorActionService(db)
    result = await service.execute(
        resource_type=request.resource_type,
        action=request.action,
        resource_ids=request.resource_ids,
        tenant_id=_tenant_id(claims),
        actor_id=_actor_id(claims),
        is_admin=_is_admin(claims),
        confirm=request.confirm,
        reason=request.reason,
        input_data=request.input_data,
        idempotency_key=idempotency_key,
    )
    return {
        **result,
        "items": [
            {
                "resource_id": item.resource_id,
                "status": item.status,
                "error_code": item.error_code,
                "detail": item.detail,
                "result": _serialize_result(item.result),
            }
            for item in result["items"]
        ],
    }
