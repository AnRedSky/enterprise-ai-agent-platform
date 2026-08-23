from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion


class AgentRepository:
    """Agent 持久化访问。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_owner(self, owner_id: UUID) -> list[Agent]:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.owner_id == owner_id)
            .order_by(Agent.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, agent_id: UUID) -> Agent | None:
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def list_versions(self, agent_id: UUID) -> list[AgentVersion]:
        result = await self.db.execute(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_published_version(self, agent: Agent) -> AgentVersion | None:
        if not agent.published_version_id:
            return None
        result = await self.db.execute(
            select(AgentVersion).where(
                AgentVersion.id == agent.published_version_id,
                AgentVersion.agent_id == agent.id,
            )
        )
        return result.scalar_one_or_none()

    async def get_version(self, agent_id: UUID, version_id: UUID) -> AgentVersion | None:
        result = await self.db.execute(
            select(AgentVersion).where(
                AgentVersion.id == version_id,
                AgentVersion.agent_id == agent_id,
            )
        )
        return result.scalar_one_or_none()
