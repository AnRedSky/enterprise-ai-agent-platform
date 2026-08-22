from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion, Message, Session, User
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization, OrganizationMembership


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, session_id: UUID | None, user_id: UUID, agent_id: UUID):
        if session_id:
            result = await self.db.execute(select(Session).where(Session.id == session_id, Session.user_id == user_id, Session.agent_id == agent_id))
            session = result.scalar_one_or_none()
            if not session:
                raise HTTPException(404, "会话不存在")
            return session
        session = Session(user_id=user_id, agent_id=agent_id)
        self.db.add(session)
        await self.db.flush()
        return session

    async def history(self, session_id: UUID, user_id: UUID):
        owner = await self.db.execute(select(Session).where(Session.id == session_id, Session.user_id == user_id))
        if not owner.scalar_one_or_none():
            raise HTTPException(404, "会话不存在")
        result = await self.db.execute(select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc()))
        return list(result.scalars().all())

    async def add_message(self, session_id: UUID, role: str, content: str):
        message = Message(session_id=session_id, role=role, content=content)
        self.db.add(message)
        await self.db.flush()
        return message

    async def resolve_model_profile(self, profile_id: UUID, user_id: UUID) -> tuple[ModelProfile, ModelProvider]:
        result = await self.db.execute(
            select(ModelProfile, ModelProvider)
            .join(ModelProvider, ModelProvider.id == ModelProfile.provider_id)
            .join(Organization, Organization.id == ModelProvider.organization_id)
            .join(User, User.tenant_id == Organization.tenant_id)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                ModelProfile.id == profile_id,
                ModelProfile.model_type == "chat",
                ModelProfile.enabled.is_(True),
                ModelProvider.enabled.is_(True),
                User.id == user_id,
                Organization.status == "active",
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.status == "active",
            )
        )
        row = result.first()
        if row is None:
            raise HTTPException(409, "Model Profile 不存在、未启用或当前用户无权使用")
        return row

    async def load_runtime(self, agent_id: UUID):
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(404, "Agent 不存在")
        if agent.status != "published" or not agent.published_version_id:
            raise HTTPException(409, "Agent 尚未发布可运行版本")
        version_result = await self.db.execute(
            select(AgentVersion).where(
                AgentVersion.id == agent.published_version_id,
                AgentVersion.agent_id == agent.id,
            )
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise HTTPException(409, "Agent 发布版本不存在")
        profile = None
        provider = None
        if version.model_profile_id:
            profile, provider = await self.resolve_model_profile(version.model_profile_id, agent.owner_id)
        return agent, version, profile, provider
