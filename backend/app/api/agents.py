from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
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
async def create_agent(p: AgentCreate, claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    agent, version = await AgentRegistry(db).create(UUID(claims["sub"]), **p.model_dump())
    return {"id": agent.id, "name": agent.name, "version": version.version, "model_id": version.model_id, "status": agent.status}

@router.get("")
async def list_agents(claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    agents = await AgentRegistry(db).list(UUID(claims["sub"]))
    return [{"id": a.id, "name": a.name, "description": a.description, "status": a.status} for a in agents]

@router.get("/{agent_id}/versions")
async def list_versions(agent_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return await registry.versions(agent_id)

@router.post("/{agent_id}/versions")
async def create_version(agent_id: UUID, p: VersionCreate, claims=Depends(require_roles("user", "admin")), db: AsyncSession = Depends(get_db)):
    registry = AgentRegistry(db)
    agent = await registry.get(agent_id, UUID(claims["sub"]), "admin" in claims.get("roles", []))
    return await registry.create_version(agent, p.system_prompt, p.model_id)
