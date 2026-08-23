from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion


class AgentRegistry:
    """Agent 生命周期与版本管理。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        owner_id: UUID,
        name: str,
        description: str,
        system_prompt: str,
        model_id: str,
        model_profile_id: UUID | None = None,
        knowledge_config: dict | None = None,
    ):
        agent = Agent(owner_id=owner_id, name=name, description=description)
        self.db.add(agent)
        await self.db.flush()
        version = AgentVersion(
            agent_id=agent.id,
            version="1.0.0",
            system_prompt=system_prompt,
            model_id=model_id,
            model_profile_id=model_profile_id,
            knowledge_config=knowledge_config or {},
        )
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

    async def published_version(self, agent: Agent):
        if not agent.published_version_id:
            return None
        result = await self.db.execute(
            select(AgentVersion).where(
                AgentVersion.id == agent.published_version_id,
                AgentVersion.agent_id == agent.id,
            )
        )
        return result.scalar_one_or_none()

    async def create_version(
        self,
        agent: Agent,
        system_prompt: str,
        model_id: str,
        model_profile_id: UUID | None = None,
        knowledge_config: dict | None = None,
    ):
        if agent.status == "archived":
            raise HTTPException(409, "归档 Agent 不允许创建新版本")
        versions = await self.versions(agent.id)
        max_minor = -1
        for item in versions:
            try:
                major, minor, _patch = (int(part) for part in item.version.split("."))
            except ValueError:
                continue
            if major == 1 and minor > max_minor:
                max_minor = minor
        version = AgentVersion(
            agent_id=agent.id,
            version=f"1.{max_minor + 1}.0",
            system_prompt=system_prompt,
            model_id=model_id,
            model_profile_id=model_profile_id,
            knowledge_config=knowledge_config or {},
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def publish(self, agent: Agent, version_id: UUID):
        if agent.status == "archived":
            raise HTTPException(409, "归档 Agent 不允许发布")
        result = await self.db.execute(
            select(AgentVersion).where(
                AgentVersion.id == version_id,
                AgentVersion.agent_id == agent.id,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(404, "Agent 版本不存在")
        agent.published_version_id = version.id
        agent.status = "published"
        await self.db.commit()
        await self.db.refresh(agent)
        return agent, version

    async def archive(self, agent: Agent):
        if agent.status == "archived":
            return agent
        agent.status = "archived"
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
