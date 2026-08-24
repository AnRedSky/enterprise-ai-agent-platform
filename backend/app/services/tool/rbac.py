"""Tool 权限服务。

职责：基于 Agent 所有权与管理员角色判断当前执行者是否可以调用指定 Tool。
边界：不负责 Tool 执行、API 鉴权或 Repository 实现；依赖 SQLAlchemy Session 与核心身份模型。
"""

from sqlalchemy import select

from app.models.core import Agent, Role, UserRole


class ToolRBACService:
    """Tool 执行权限判断边界。"""

    def __init__(self, session):
        self.session = session

    async def can_execute(self, actor_id, agent_id, tool_id) -> bool:
        agent = await self.session.scalar(select(Agent).where(Agent.id == agent_id))
        if agent is None or agent.status not in {"active", "published"}:
            return False
        if agent.owner_id == actor_id:
            return True
        result = await self.session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == actor_id, Role.name == "admin")
        )
        return result.scalar_one_or_none() == "admin"
