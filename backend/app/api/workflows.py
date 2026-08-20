from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.services.workflow_registry import WorkflowRegistry
from app.services.workflow_trigger import WorkflowTriggerService

router = APIRouter()


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class WorkflowVersionCreate(BaseModel):
    definition: dict = Field(default_factory=dict)


class WorkflowTriggerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    trigger_type: str = Field(default="manual", min_length=1, max_length=30)
    config: dict = Field(default_factory=dict)


class WorkflowTriggerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = None
    config: dict | None = None


class WorkflowTriggerInvoke(BaseModel):
    input_data: dict = Field(default_factory=dict)


def _tenant_id(claims: dict) -> UUID:
    try:
        return UUID(claims["tenant_id"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("Token 缺少有效 tenant_id")


def _workflow_response(workflow):
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "owner_id": workflow.owner_id,
        "tenant_id": workflow.tenant_id,
        "status": workflow.status,
        "published_version_id": workflow.published_version_id,
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
    }


def _version_response(version):
    return {
        "id": version.id,
        "workflow_id": version.workflow_id,
        "version": version.version,
        "definition": version.definition,
        "status": version.status,
        "created_by": version.created_by,
        "created_at": version.created_at,
    }


def _trigger_response(trigger):
    return {
        "id": trigger.id,
        "workflow_id": trigger.workflow_id,
        "tenant_id": trigger.tenant_id,
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "status": trigger.status,
        "created_by": trigger.created_by,
        "config": trigger.config,
        "created_at": trigger.created_at,
        "updated_at": trigger.updated_at,
    }


def _execution_response(execution):
    return {
        "id": execution.id,
        "tenant_id": execution.tenant_id,
        "workflow_id": execution.workflow_id,
        "workflow_version_id": execution.workflow_version_id,
        "created_by": execution.created_by,
        "retry_of_execution_id": execution.retry_of_execution_id,
        "idempotency_key": execution.idempotency_key,
        "status": execution.status,
        "current_node_id": execution.current_node_id,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "error_code": execution.error_code,
        "error_message": execution.error_message,
        "started_at": execution.started_at,
        "ended_at": execution.ended_at,
        "created_at": execution.created_at,
    }


@router.get("")
async def list_workflows(claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = WorkflowRegistry(db)
    workflows = await registry.list(_tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_workflow_response(item) for item in workflows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await WorkflowRegistry(db).create(_tenant_id(claims), UUID(claims["sub"]), payload.name, payload.description)
    return _workflow_response(workflow)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _workflow_response(workflow)


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    workflow = await registry.update(workflow, payload.name, payload.description)
    return _workflow_response(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    await registry.delete(workflow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workflow_id}/triggers")
async def list_workflow_triggers(workflow_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_trigger_response(item) for item in await WorkflowTriggerService(db).list(workflow)]


@router.post("/{workflow_id}/triggers", status_code=status.HTTP_201_CREATED)
async def create_workflow_trigger(
    workflow_id: UUID,
    payload: WorkflowTriggerCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    trigger = await WorkflowTriggerService(db).create(workflow, UUID(claims["sub"]), payload.name, payload.trigger_type, payload.config)
    return _trigger_response(trigger)


@router.get("/{workflow_id}/triggers/{trigger_id}")
async def get_workflow_trigger(workflow_id: UUID, trigger_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _trigger_response(await WorkflowTriggerService(db).get(workflow, trigger_id))


@router.patch("/{workflow_id}/triggers/{trigger_id}")
async def update_workflow_trigger(
    workflow_id: UUID,
    trigger_id: UUID,
    payload: WorkflowTriggerUpdate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    trigger_service = WorkflowTriggerService(db)
    trigger = await trigger_service.get(workflow, trigger_id)
    return _trigger_response(await trigger_service.update(trigger, payload.name, payload.status, payload.config))


@router.delete("/{workflow_id}/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow_trigger(
    workflow_id: UUID,
    trigger_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    trigger_service = WorkflowTriggerService(db)
    await trigger_service.delete(await trigger_service.get(workflow, trigger_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workflow_id}/triggers/{trigger_id}/invoke")
async def invoke_workflow_trigger(
    workflow_id: UUID,
    trigger_id: UUID,
    payload: WorkflowTriggerInvoke,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await WorkflowRegistry(db).get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    trigger_service = WorkflowTriggerService(db)
    trigger = await trigger_service.get(workflow, trigger_id)
    execution = await trigger_service.invoke(
        workflow,
        trigger,
        UUID(claims["sub"]),
        payload.input_data,
        idempotency_key=idempotency_key,
        is_admin="admin" in claims.get("roles", []),
    )
    return _execution_response(execution)


@router.get("/{workflow_id}/versions")
async def list_workflow_versions(workflow_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = WorkflowRegistry(db)
    await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_version_response(item) for item in await registry.versions(workflow_id)]


@router.post("/{workflow_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_workflow_version(
    workflow_id: UUID,
    payload: WorkflowVersionCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    version = await registry.create_version(workflow, UUID(claims["sub"]), payload.definition)
    return _version_response(version)


@router.get("/{workflow_id}/versions/{version_id}")
async def get_workflow_version(
    workflow_id: UUID,
    version_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _version_response(await registry.get_version(workflow_id, version_id))


@router.post("/{workflow_id}/versions/{version_id}/publish")
async def publish_workflow_version(
    workflow_id: UUID,
    version_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, _tenant_id(claims), UUID(claims["sub"]), "admin" in claims.get("roles", []))
    version = await registry.get_version(workflow_id, version_id)
    return _version_response(await registry.publish(workflow, version, UUID(claims["sub"])))
