"""Tool 数据访问适配器。

职责：封装 Tool、AgentTool 绑定与 AuditLog 的 SQLAlchemy 持久化操作。
边界：不承载权限、执行策略或 API 协议；依赖调用方注入 ORM 模型与数据库 Session。
"""

from __future__ import annotations

from sqlalchemy import select


class SqlAlchemyToolRepository:
    """Tool 与 AgentTool 的统一数据访问边界。"""

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
    """AuditLog 的统一数据访问边界。"""

    def __init__(self, session, audit_model):
        self.session = session
        self.audit_model = audit_model

    async def create(self, values: dict):
        record = self.audit_model(**values)
        self.session.add(record)
        await self.session.flush()
        return record
