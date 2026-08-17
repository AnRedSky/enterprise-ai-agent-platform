from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.core import Agent, AgentVersion

class AgentRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, owner_id: UUID, name: str, description: str, system_prompt: str, model_id: str):
        agent = Agent(owner_id=owner_id, name=name, description=description)
        self.db.add(agent)
        await self.db.flush()
        version = AgentVersion(agent_id=agent.id, version="1.0.0", system_prompt=system_prompt, model_id=model_id)
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent, version

    async def list(self, owner_id: UUID):
        result = await self.db.execute(select(Agent).where(Agent.owner_id == owner_id).order_by(Agent.created_at.desc()))
        return list(result.scalars().all())

    async def get(self, agent_id: UUID, owner_id: UUID, admin: bool = False):
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent or (not admin and agent.owner_id != owner_id):
            raise HTTPException(404, "Agent 不存在")
        return agent

    async def versions(self, agent_id: UUID):
        result = await self.db.execute(select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.created_at.desc()))
        return list(result.scalars().all())

    async def create_version(self, agent: Agent, system_prompt: str, model_id: str):
        versions = await self.versions(agent.id)
        next_major = len(versions) + 1
        version = AgentVersion(agent_id=agent.id, version=f"1.{next_major - 1}.0", system_prompt=system_prompt, model_id=model_id)
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version
