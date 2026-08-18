from __future__ import annotations

from sqlalchemy import select


class SqlAlchemyToolRepository:
    """Database adapter; ORM models are supplied by the application layer."""

    def __init__(self, session, tool_model, agent_tool_model):
        self.session = session
        self.tool_model = tool_model
        self.agent_tool_model = agent_tool_model

    async def get(self, tool_id: int):
        result = await self.session.execute(select(self.tool_model).where(self.tool_model.id == tool_id))
        return result.scalar_one_or_none()

    async def get_binding(self, agent_id: int, tool_id: int):
        result = await self.session.execute(
            select(self.agent_tool_model).where(
                self.agent_tool_model.agent_id == agent_id,
                self.agent_tool_model.tool_id == tool_id,
            )
        )
        return result.scalar_one_or_none()


class SqlAlchemyAuditRepository:
    def __init__(self, session, audit_model):
        self.session = session
        self.audit_model = audit_model

    async def create(self, values: dict):
        record = self.audit_model(**values)
        self.session.add(record)
        await self.session.flush()
        return record
