from sqlalchemy import select

from app.models.core import Agent, User, UserRole, Role


class ToolRBACService:
    """Minimal DB-backed authorization adapter for tool execution.

    Owners and users with the admin role may invoke tools for an agent. This
    keeps authorization in the runtime rather than relying on API handlers.
    """

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
