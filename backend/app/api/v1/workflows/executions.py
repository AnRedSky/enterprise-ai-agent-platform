"""Workflow Execution API 路由。

职责：提供 Workflow Execution 的创建、运行、取消、重试、状态转换与追踪协议。
边界：只负责 HTTP 协议、鉴权和响应组装；Execution 生命周期规则统一由 app.services.workflow 领域服务处理。
关键依赖：WorkflowRegistry、WorkflowExecutionService、SQLAlchemy AsyncSession 与 Workflow ORM。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.services.workflow import WorkflowExecutionService, WorkflowRegistry

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
            "retry_of_execution_id": item.retry_of_execution_id, "idempotency_key": item.idempotency_key,
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


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    """List executions belonging to a workflow, including scheduler-created executions.

    Authorization is based on workflow ownership rather than execution.created_by because
    scheduled executions are created by the scheduler service identity.
    """
    tenant_id = _tenant_id(claims)
    actor_id = UUID(claims["sub"])
    is_admin = "admin" in claims.get("roles", [])
    workflow_query = select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
    if not is_admin:
        workflow_query = workflow_query.where(Workflow.owner_id == actor_id)
    workflow = (await db.execute(workflow_query)).scalar_one_or_none()
    if workflow is None:
        raise HTTPException(404, "Workflow 不存在")

    rows = (await db.execute(
        select(WorkflowExecution)
        .where(
            WorkflowExecution.tenant_id == tenant_id,
            WorkflowExecution.workflow_id == workflow_id,
        )
        .order_by(WorkflowExecution.created_at.desc(), WorkflowExecution.id.desc())
    )).scalars().all()
    return [_execution_response(item) for item in rows]


@router.post("/{workflow_id}/executions", status_code=201)
async def create_execution(workflow_id: UUID, payload: WorkflowExecutionCreate,
                           idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
                           claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    if workflow.published_version_id is None:
        raise HTTPException(409, "Workflow 没有已发布版本")
    version = await registry.get_version(workflow.id, workflow.published_version_id)
    execution = await WorkflowExecutionService(db).create(
        workflow, version, UUID(claims["sub"]), payload.input_data, idempotency_key
    )
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
