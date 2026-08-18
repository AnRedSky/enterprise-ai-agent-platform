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


class PublishRequest(BaseModel):
    version_id: UUID


@router.post("")
async def create_agent(p: AgentCreate, claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    agent, version = await AgentRegistry(db).create(UUID(claims["sub"]), **p.model_dump())
    return {"id": agent.id, "name": agent.name, "description": agent.description, "version": version.version, "model_id": version.model_id, "status": agent.status, "published_version_id": agent.published_version_id}


@router.get("")
async def list_agents(claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agents = await registry.list(UUID(claims["sub"]))
    if not agents:
        return []
    versions_result = await db.execute(select(AgentVersion).where(AgentVersion.agent_id.in_([agent.id for agent in agents])).order_by(AgentVersion.created_at.desc()))
    latest_versions: dict[UUID, AgentVersion] = {}
    for version in versions_result.scalars().all():
        latest_versions.setdefault(version.agent_id, version)
    result = []
    for agent in agents:
        published = await registry.published_version(agent)
        latest = latest_versions.get(agent.id)
        result.append({
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "model_id": published.model_id if published else (latest.model_id if latest else None),
            "version": published.version if published else (latest.version if latest else None),
            "status": agent.status,
            "published_version_id": agent.published_version_id,
            "created_at": agent.created_at,
        })
    return result


@router.get("/{agent_id}/versions")
async def list_versions(agent_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    published_id = agent.published_version_id
    return [
        {"id": v.id, "agent_id": v.agent_id, "version": v.version, "system_prompt": v.system_prompt, "model_id": v.model_id, "created_at": v.created_at, "is_published": v.id == published_id}
        for v in await registry.versions(agent_id)
    ]


@router.get("/{agent_id}/published-version")
async def get_published_version(agent_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    version = await registry.published_version(agent)
    if not version:
        from fastapi import HTTPException
        raise HTTPException(404, "Agent 尚未发布版本")
    return {"id": version.id, "agent_id": version.agent_id, "version": version.version, "system_prompt": version.system_prompt, "model_id": version.model_id, "created_at": version.created_at, "is_published": True}


@router.post("/{agent_id}/versions")
async def create_version(agent_id: UUID, p: VersionCreate, claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return await registry.create_version(agent, p.system_prompt, p.model_id)


@router.post("/{agent_id}/publish")
async def publish_agent(agent_id: UUID, p: PublishRequest, claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    agent, version = await registry.publish(agent, p.version_id)
    return {"id": agent.id, "status": agent.status, "published_version_id": agent.published_version_id, "version": version.version, "model_id": version.model_id}


@router.post("/{agent_id}/archive")
async def archive_agent(agent_id: UUID, claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    agent = await registry.archive(agent)
    return {"id": agent.id, "status": agent.status, "published_version_id": agent.published_version_id}
