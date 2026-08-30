"""Runtime Operator Action HTTP 协议模块。

职责：暴露统一的 Operator Action 可用性查询与执行接口。
边界：只负责身份、租户上下文、请求校验和响应组装；不实现 Workflow / Trigger 生命周期。
关键依赖：OperatorActionGovernanceService、FastAPI、数据库 Session 与认证依赖。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims, require_roles
from app.dependencies.db import get_db
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


router = APIRouter(prefix="/api/v1/runtime/operator-actions", tags=["runtime-operator-actions"])


class OperatorActionRequest(BaseModel):
    """Operator Action 执行请求。"""

    confirm: bool = False
    reason: str | None = Field(default=None, max_length=500)
    input_data: dict[str, Any] = Field(default_factory=dict)


def _claims(credentials=Depends(bearer)) -> dict:
    """解析当前身份上下文，不允许请求体提交 tenant_id。"""
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    """从已验证身份中取得租户标识。"""
    try:
        return UUID(claims["tenant_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token 缺少有效 tenant_id") from exc


def _actor_id(claims: dict) -> UUID:
    """从已验证身份中取得操作人标识。"""
    try:
        return UUID(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token 缺少有效用户标识") from exc


def _is_admin(claims: dict) -> bool:
    """判断当前身份是否具备本租户管理员权限。"""
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return "admin" in roles


def _execution_response(item: Any) -> dict[str, Any]:
    """转换 Workflow Execution 响应，并保持现有 API Contract 字段。"""
    return {
        "id": item.id,
        "tenant_id": item.tenant_id,
        "workflow_id": item.workflow_id,
        "workflow_version_id": item.workflow_version_id,
        "created_by": item.created_by,
        "retry_of_execution_id": item.retry_of_execution_id,
        "resume_of_execution_id": item.resume_of_execution_id,
        "resume_checkpoint_sequence": item.resume_checkpoint_sequence,
        "idempotency_key": item.idempotency_key,
        "status": item.status,
        "current_node_id": item.current_node_id,
        "input_data": item.input_data,
        "output_data": item.output_data,
        "error_code": item.error_code,
        "error_message": item.error_message,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "created_at": item.created_at,
    }


def _trigger_response(item: Any) -> dict[str, Any]:
    """转换 Workflow Trigger 响应并隐藏 webhook secret。"""
    config = dict(item.config or {})
    if item.trigger_type == "webhook":
        config.pop("secret_hash", None)
        config["secret_configured"] = True
    return {
        "id": item.id,
        "workflow_id": item.workflow_id,
        "tenant_id": item.tenant_id,
        "name": item.name,
        "trigger_type": item.trigger_type,
        "status": item.status,
        "created_by": item.created_by,
        "config": config,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/workflow-executions/{execution_id}")
async def workflow_execution_action_availability(
    execution_id: UUID,
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """返回当前用户可访问 Execution 的统一操作可用性。"""
    return await OperatorActionGovernanceService(db).execution_availability(
        execution_id, _tenant_id(claims), _actor_id(claims), _is_admin(claims),
    )


@router.post("/workflow-executions/{execution_id}/{action}")
async def execute_workflow_execution_action(
    execution_id: UUID,
    action: str,
    request: OperatorActionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    claims: dict = Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """执行 Workflow Execution Operator Action，生命周期继续委托现有领域服务。"""
    try:
        result = await OperatorActionGovernanceService(db).execute_execution(
            execution_id,
            _tenant_id(claims),
            _actor_id(claims),
            _is_admin(claims),
            action,
            confirm=request.confirm,
            reason=request.reason,
            idempotency_key=idempotency_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Operator Action 执行失败") from exc
    return {"resource_type": "workflow_execution", "action": action, "result": _execution_response(result)}


@router.get("/workflow-triggers/{trigger_id}")
async def workflow_trigger_action_availability(
    trigger_id: UUID,
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """返回当前用户可访问 Trigger 的统一操作可用性。"""
    return await OperatorActionGovernanceService(db).trigger_availability(
        trigger_id, _tenant_id(claims), _actor_id(claims), _is_admin(claims),
    )


@router.post("/workflow-triggers/{trigger_id}/{action}")
async def execute_workflow_trigger_action(
    trigger_id: UUID,
    action: str,
    request: OperatorActionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    claims: dict = Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """执行 Workflow Trigger Operator Action，生命周期继续委托现有 Trigger 服务。"""
    try:
        result = await OperatorActionGovernanceService(db).execute_trigger(
            trigger_id,
            _tenant_id(claims),
            _actor_id(claims),
            _is_admin(claims),
            action,
            confirm=request.confirm,
            input_data=request.input_data,
            idempotency_key=idempotency_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Operator Action 执行失败") from exc
    if hasattr(result, "workflow_id") and hasattr(result, "status") and hasattr(result, "workflow_version_id"):
        return {"resource_type": "workflow_execution", "action": action, "result": _execution_response(result)}
    return {"resource_type": "workflow_trigger", "action": action, "result": _trigger_response(result)}
