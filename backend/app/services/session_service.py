from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.core import Agent, AgentVersion, Message, Session

class SessionService:
    def __init__(self, db: AsyncSession): self.db = db

    async def get_or_create(self, session_id: UUID | None, user_id: UUID, agent_id: UUID):
        if session_id:
            result = await self.db.execute(select(Session).where(Session.id == session_id, Session.user_id == user_id, Session.agent_id == agent_id))
            session = result.scalar_one_or_none()
            if not session: raise HTTPException(404, "会话不存在")
            return session
        session = Session(user_id=user_id, agent_id=agent_id)
        self.db.add(session); await self.db.flush(); return session

    async def history(self, session_id: UUID, user_id: UUID):
        owner = await self.db.execute(select(Session).where(Session.id == session_id, Session.user_id == user_id))
        if not owner.scalar_one_or_none(): raise HTTPException(404, "会话不存在")
        result = await self.db.execute(select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc()))
        return list(result.scalars().all())

    async def add_message(self, session_id: UUID, role: str, content: str):
        message = Message(session_id=session_id, role=role, content=content)
        self.db.add(message); await self.db.flush(); return message

    async def load_runtime(self, agent_id: UUID):
        result = await self.db.execute(select(Agent, AgentVersion).join(AgentVersion, AgentVersion.agent_id == Agent.id).where(Agent.id == agent_id).order_by(AgentVersion.created_at.desc()))
        row = result.first()
        if not row: raise HTTPException(404, "Agent 或版本不存在")
        return row[0], row[1]
