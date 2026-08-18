from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.models.core import AgentVersion
from app.services.agent_registry import AgentRegistry

router = APIRouter()


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    system_prompt: str = "你是企业级 AI 助手。"
    model_id: str = "mock-model"


class VersionCreate(BaseModel):
    system_prompt: str = Field(min_length=1)
    model_id: str = Field(min_length=1)


@router.post("")
async def create_agent(
    p: AgentCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    agent, version = await AgentRegistry(db).create(UUID(claims["sub"]), **p.model_dump())
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "version": version.version,
        "model_id": version.model_id,
        "status": agent.status,
    }


@router.get("")
async def list_agents(
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    agents = await AgentRegistry(db).list(UUID(claims["sub"]))
    if not agents:
        return []

    versions_result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id.in_([agent.id for agent in agents]))
        .order_by(AgentVersion.created_at.desc())
    )
    latest_versions: dict[UUID, AgentVersion] = {}
    for version in versions_result.scalars().all():
        latest_versions.setdefault(version.agent_id, version)

    return [
        {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "model_id": latest_versions[agent.id].model_id if agent.id in latest_versions else None,
            "version": latest_versions[agent.id].version if agent.id in latest_versions else None,
            "status": agent.status,
            "created_at": agent.created_at,
        }
        for agent in agents
    ]


@router.get("/{agent_id}/versions")
async def list_versions(
    agent_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    registry = AgentRegistry(db)
    await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return await registry.versions(agent_id)


@router.post("/{agent_id}/versions")
async def create_version(
    agent_id: UUID,
    p: VersionCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return await registry.create_version(agent, p.system_prompt, p.model_id)
