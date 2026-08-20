from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.models.workflow import WorkflowVersion
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


class ExecutionCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


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
    return {"id": item.id, "tenant_id": item.tenant_id, "workflow_id": item.workflow_id,
            "workflow_version_id": item.workflow_version_id, "created_by": item.created_by,
            "retry_of_execution_id": item.retry_of_execution_id,
            "status": item.status, "current_node_id": item.current_node_id, "input_data": item.input_data,
            "output_data": item.output_data, "error_code": item.error_code, "error_message": item.error_message,
            "started_at": item.started_at, "ended_at": item.ended_at, "created_at": item.created_at}


def _node_response(item):
    return {"id": item.id, "execution_id": item.execution_id, "node_id": item.node_id, "status": item.status,
            "attempt": item.attempt, "input_data": item.input_data, "output_data": item.output_data,
            "error_code": item.error_code, "error_message": item.error_message,
            "started_at": item.started_at, "ended_at": item.ended_at, "created_at": item.created_at}


def _trace_response(item):
    return {"id": item.id, "tenant_id": item.tenant_id, "execution_id": item.execution_id,
            "workflow_id": item.workflow_id, "workflow_version_id": item.workflow_version_id,
            "node_id": item.node_id, "event_type": item.event_type, "status": item.status,
            "trace_id": item.trace_id, "actor_id": item.actor_id, "data": item.data,
            "error_code": item.error_code, "error_message": item.error_message, "created_at": item.created_at}


@router.post("/{workflow_id}/executions", status_code=201)
async def create_execution(workflow_id: UUID, payload: WorkflowExecutionCreate,
                           claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    if workflow.published_version_id is None:
        raise HTTPException(409, "Workflow 没有已发布版本")
    version = await registry.get_version(workflow.id, workflow.published_version_id)
    execution = await WorkflowExecutionService(db).create(workflow, version, UUID(claims["sub"]), payload.input_data)
    return _execution_response(execution)


@router.post("/executions/{execution_id}/run")
async def run_execution(execution_id: UUID, claims=Depends(require_roles("user", "admin")),
                        db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    is_admin = "admin" in claims.get("roles", [])
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), is_admin)
    version = (await db.execute(select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id))).scalar_one_or_none()
    if version is None:
        raise HTTPException(409, "Workflow Execution 版本不存在")
    return _execution_response(await service.run(execution, version, UUID(claims["sub"]), is_admin))


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: UUID, payload: ExecutionCancel,
                           claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    actor_id = UUID(claims["sub"])
    execution = await service.get(execution_id, _tenant_id(claims), actor_id, "admin" in claims.get("roles", []))
    return _execution_response(await service.cancel(execution, actor_id, payload.reason))


@router.post("/executions/{execution_id}/retry", status_code=201)
async def retry_execution(execution_id: UUID, claims=Depends(require_roles("user", "admin")),
                          db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    actor_id = UUID(claims["sub"])
    execution = await service.get(execution_id, _tenant_id(claims), actor_id, "admin" in claims.get("roles", []))
    return _execution_response(await service.retry(execution, actor_id))


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    execution = await WorkflowExecutionService(db).get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _execution_response(execution)


@router.get("/executions/{execution_id}/nodes")
async def list_execution_nodes(execution_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_node_response(item) for item in await service.nodes(execution)]


@router.get("/executions/{execution_id}/trace")
async def list_execution_trace(execution_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_trace_response(item) for item in await service.trace(execution)]


@router.post("/executions/{execution_id}/transition")
async def transition_execution(execution_id: UUID, payload: ExecutionTransition,
                               claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    actor_id = UUID(claims["sub"])
    execution = await service.get(execution_id, _tenant_id(claims), actor_id, "admin" in claims.get("roles", []))
    return _execution_response(await service.transition(execution, payload.status, payload.node_id,
                                                        payload.error_code, payload.error_message, payload.output_data,
                                                        actor_id=actor_id))


@router.post("/executions/{execution_id}/nodes/transition")
async def transition_node(execution_id: UUID, payload: NodeTransition,
                          claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    service = WorkflowExecutionService(db)
    execution = await service.get(execution_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    node = await service.transition_node(execution, payload.node_id, payload.status, payload.input_data,
                                         payload.output_data, payload.error_code, payload.error_message)
    return _node_response(node)
