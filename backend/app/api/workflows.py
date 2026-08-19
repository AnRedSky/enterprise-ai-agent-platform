from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.services.workflow_registry import WorkflowRegistry

router = APIRouter()


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class WorkflowVersionCreate(BaseModel):
    definition: dict = Field(default_factory=dict)


def _workflow_response(workflow):
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "owner_id": workflow.owner_id,
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


@router.get("")
async def list_workflows(claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = WorkflowRegistry(db)
    workflows = await registry.list(UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_workflow_response(item) for item in workflows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await WorkflowRegistry(db).create(UUID(claims["sub"]), payload.name, payload.description)
    return _workflow_response(workflow)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    workflow = await WorkflowRegistry(db).get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _workflow_response(workflow)


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    workflow = await registry.update(workflow, payload.name, payload.description)
    return _workflow_response(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    await registry.delete(workflow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workflow_id}/versions")
async def list_workflow_versions(workflow_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = WorkflowRegistry(db)
    await registry.get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return [_version_response(item) for item in await registry.versions(workflow_id)]


@router.post("/{workflow_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_workflow_version(
    workflow_id: UUID,
    payload: WorkflowVersionCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
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
    await registry.get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return _version_response(await registry.get_version(workflow_id, version_id))


@router.post("/{workflow_id}/versions/{version_id}/publish")
async def publish_workflow_version(
    workflow_id: UUID,
    version_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = WorkflowRegistry(db)
    workflow = await registry.get(workflow_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    version = await registry.get_version(workflow_id, version_id)
    return _version_response(await registry.publish(workflow, version, UUID(claims["sub"])))
