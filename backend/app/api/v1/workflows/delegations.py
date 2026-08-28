"""Workflow Execution Delegation API。

职责：暴露受治理 Agent Delegation 的创建、查询与取消 HTTP Contract。
边界：不执行 Worker、不直接修改父 Execution 状态；领域规则统一由 AgentDelegationService 处理。
关键依赖：现有 JWT/RBAC、Workflow Execution tenant scope 与 Agent Delegation Service。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.services.agent_delegation import AgentDelegationService

router = APIRouter()


class DelegationCreate(BaseModel):
    """创建 Delegation 的显式上下文与治理参数。"""

    target_agent_version_id: UUID
    delegation_key: str = Field(min_length=1, max_length=128)
    input_data: dict = Field(default_factory=dict)
    selected_context_refs: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    max_delegation_depth: int | None = Field(default=None, ge=1, le=20)
    max_active_delegations: int | None = Field(default=None, ge=1, le=100)
    timeout_seconds: int | None = Field(default=None, ge=1, le=86_400)
    model_budget: dict | None = None


def _tenant_id(claims: dict) -> UUID:
    """从 JWT claims 读取 tenant identity。"""
    try:
        return UUID(claims["tenant_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Token 缺少有效 tenant_id") from exc


def _response(item):
    """将 Durable Delegation 转换为不暴露内部 Worker lease 的 API 响应。"""
    return {
        "id": item.id,
        "status": item.status,
        "source_execution_id": item.source_execution_id,
        "source_agent_version_id": item.source_agent_version_id,
        "target_agent_version_id": item.target_agent_version_id,
        "delegation_key": item.delegation_key,
        "input_data": item.input_data,
        "selected_context_refs": item.selected_context_refs,
        "allowed_tools": item.allowed_tools,
        "model_profile_id": item.model_profile_id,
        "model_budget": item.model_budget,
        "max_delegation_depth": item.max_delegation_depth,
        "max_active_delegations": item.max_active_delegations,
        "timeout_seconds": item.timeout_seconds,
        "depth": item.depth,
        "worker_execution_id": item.worker_execution_id,
        "trace_id": item.trace_id,
        "error_code": item.error_code,
        "error_message": item.error_message,
        "created_at": item.created_at,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "timeout_at": item.timeout_at,
    }


@router.post("/{execution_id}/delegations", status_code=201)
async def create_delegation(
    execution_id: UUID,
    payload: DelegationCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """创建受治理 Delegation；重复业务 key 收敛到已有 Durable fact。"""
    item = await AgentDelegationService(db).create(
        tenant_id=_tenant_id(claims),
        source_execution_id=execution_id,
        actor_id=UUID(claims["sub"]),
        target_agent_version_id=payload.target_agent_version_id,
        delegation_key=payload.delegation_key,
        input_data=payload.input_data,
        selected_context_refs=payload.selected_context_refs,
        allowed_tools=payload.allowed_tools,
        max_delegation_depth=payload.max_delegation_depth,
        max_active_delegations=payload.max_active_delegations,
        timeout_seconds=payload.timeout_seconds,
        model_budget=payload.model_budget,
    )
    return _response(item)


@router.get("/{execution_id}/delegations")
async def list_delegations(
    execution_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    """查询指定 Execution 的全部 Delegation。"""
    items = await AgentDelegationService(db).list(
        tenant_id=_tenant_id(claims),
        source_execution_id=execution_id,
        actor_id=UUID(claims["sub"]),
        admin="admin" in claims.get("roles", []),
    )
    return [_response(item) for item in items]


@router.get("/{execution_id}/delegations/{delegation_id}")
async def get_delegation(
    execution_id: UUID,
    delegation_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    """查询单个 Delegation。"""
    item = await AgentDelegationService(db).get(
        tenant_id=_tenant_id(claims),
        source_execution_id=execution_id,
        delegation_id=delegation_id,
        actor_id=UUID(claims["sub"]),
        admin="admin" in claims.get("roles", []),
    )
    return _response(item)


@router.post("/{execution_id}/delegations/{delegation_id}/cancel")
async def cancel_delegation(
    execution_id: UUID,
    delegation_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """取消仍处于活动态的 Delegation，不改变父 Execution terminal 状态。"""
    item = await AgentDelegationService(db).cancel(
        tenant_id=_tenant_id(claims),
        source_execution_id=execution_id,
        delegation_id=delegation_id,
        actor_id=UUID(claims["sub"]),
        admin="admin" in claims.get("roles", []),
    )
    return _response(item)
