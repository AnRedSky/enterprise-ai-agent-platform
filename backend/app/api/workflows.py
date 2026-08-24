from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.services.workflow import WorkflowRegistry
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
    config = dict(trigger.config or {})
    if trigger.trigger_type == "webhook":
        config.pop("secret", None)
    return {
        "id": trigger.id,
        "workflow_id": trigger.workflow_id,
        "tenant_id": trigger.tenant_id,
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "status": trigger.status,
        "config": config,
        "created_by": trigger.created_by,
        "created_at": trigger.created_at,
        "updated_at": trigger.updated_at,
    }


@router.get("/workflows")
async def list_workflows(claims: dict = Depends(current_claims), db: AsyncSession = Depends(get_db)):
    tenant_id = _tenant_id(claims)
    owner_id = UUID(claims["sub"])
    admin = "admin" in claims.get("roles", [])
    workflows = await WorkflowRegistry(db).list(tenant_id, owner_id, admin=admin)
    return [_workflow_response(item) for item in workflows]


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(payload: WorkflowCreate, claims: dict = Depends(current_claims), db: AsyncSession = Depends(get_db)):
    tenant_id = _tenant_id(claims)
    owner_id = UUID(claims["sub"])
    workflow = await WorkflowRegistry(db).create(tenant_id, owner_id, payload.name, payload.description)
    return _workflow_response(workflow)
