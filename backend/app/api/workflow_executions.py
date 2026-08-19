from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.services.workflow_execution import WorkflowExecutionService
from app.services.workflow_registry import WorkflowRegistry

router = APIRouter()


class WorkflowExecutionCreate(BaseModel):
    input_data: dict = Field(default_factory=dict)


class ExecutionTransition(BaseModel):
    status: str
    node_id: str | None = Field(default=None, max_length=100)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = None
    output_data: dict | None = None


class NodeTransition(BaseModel):
    node_id: str = Field(min_length=1, max_length=100)
    status: str
    input_data: dict | None = None
    output_data: dict | None = None
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = None


def _tenant_id(claims: dict) -> UUID:
    try:
        return UUID(claims["tenant_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Token 缺少有效 tenant_id") from exc


def _execution_response(item):
    return {
        "id": item.id,
        "tenant_id": item.tenant_id,
        "workflow_id": item.workflow_id,
        "workflow_version_id": item.workflow_version_id,
        "created_by": item.created_by,
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


def _node_response(item):
    return {
        "id": item.id,
        "execution_id": item.execution_id,
        "node_id": item.node_id,
        "status": item.status,
        "attempt": item.attempt,
        "input_data": item.input_data,
        "output_data": item.output_data,
        "error_code": item.error_code,
        "error_message": item.error_message,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "created_at": item.created_at,
    }


@router.post("/workflows/{workflow_id}/executions", status_code=201)
async def create_execution(
    workflow_id: UUID,
    payload: WorkflowExecutionCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    if workflow.published_version_id is None:
        from fastapi import HTTPException
        raise HTTPException(409, "Workflow 没有已发布版本")
    version = await registry.get_version(workflow.id, workflow.published_version_id)
    execution = await WorkflowExecutionService(db).create(workflow, version, UUID(claims["sub"]), payload.input_data)
    return _execution_response(execution)


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _execution_response(execution)


@router.get("/executions/{execution_id}/nodes")
async def list_execution_nodes(
    execution_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_node_response(item) for item in await service.nodes(execution)]


@router.post("/executions/{execution_id}/transition")
async def transition_execution(
    execution_id: UUID,
    payload: ExecutionTransition,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _execution_response(
        await service.transition(
            execution,
            payload.status,
            payload.node_id,
            payload.error_code,
            payload.error_message,
            payload.output_data,
        )
    )


@router.post("/executions/{execution_id}/nodes/transition")
async def transition_node(
    execution_id: UUID,
    payload: NodeTransition,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    node = await service.transition_node(
        execution,
        payload.node_id,
        payload.status,
        payload.input_data,
        payload.output_data,
        payload.error_code,
        payload.error_message,
    )
    return _node_response(node)
