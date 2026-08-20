from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion, User
from app.runtime.model_gateway import ModelGateway


class WorkflowRuntime:
    """Execute the stable Phase 1.5-D sequential workflow contract.

    Definition contract:
    {"nodes": [{"id": "...", "type": "input|agent|output", "config": {...}}]}
    Nodes execute in declaration order. Branching and parallel scheduling remain
    outside this phase and must not be inferred from arbitrary definition data.
    """

    NODE_TYPES = {"input", "agent", "output"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gateway = ModelGateway()

    @classmethod
    def validate_definition(cls, definition: dict) -> list[dict]:
        nodes = definition.get("nodes") if isinstance(definition, dict) else None
        if not isinstance(nodes, list) or not nodes:
            raise HTTPException(422, "Workflow definition 必须包含非空 nodes")
        seen: set[str] = set()
        normalized: list[dict] = []
        for raw in nodes:
            if not isinstance(raw, dict):
                raise HTTPException(422, "Workflow node 必须为对象")
            node_id = raw.get("id")
            node_type = raw.get("type")
            if not isinstance(node_id, str) or not node_id or len(node_id) > 100:
                raise HTTPException(422, "Workflow node id 无效")
            if node_id in seen:
                raise HTTPException(422, f"Workflow node id 重复: {node_id}")
            if node_type not in cls.NODE_TYPES:
                raise HTTPException(422, f"不支持的 Workflow node type: {node_type}")
            seen.add(node_id)
            normalized.append({"id": node_id, "type": node_type, "config": raw.get("config") or {}})
        return normalized

    async def execute_node(
        self,
        node: dict,
        input_data: dict,
        actor_id: UUID,
        is_admin: bool,
        session_id: UUID,
        tenant_id: UUID | None = None,
    ) -> dict:
        node_type = node["type"]
        config = node["config"]
        if node_type in {"input", "output"}:
            return dict(input_data)

        agent_id = config.get("agent_id")
        try:
            agent_uuid = UUID(str(agent_id))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "agent node 必须提供有效 agent_id") from exc

        agent_query = select(Agent).join(User, User.id == Agent.owner_id).where(Agent.id == agent_uuid)
        if tenant_id is not None:
            agent_query = agent_query.where(User.tenant_id == tenant_id)
        agent = (await self.db.execute(agent_query)).scalar_one_or_none()
        if agent is None:
            raise HTTPException(404, "Workflow Agent 不存在")
        if not is_admin and agent.owner_id != actor_id:
            raise HTTPException(403, "无权执行 Workflow Agent")
        if agent.status != "published" or not agent.published_version_id:
            raise HTTPException(409, "Workflow Agent 尚未发布可运行版本")
        version = (
            await self.db.execute(
                select(AgentVersion).where(
                    AgentVersion.id == agent.published_version_id,
                    AgentVersion.agent_id == agent.id,
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise HTTPException(409, "Workflow Agent 发布版本不存在")

        prompt = config.get("prompt")
        if prompt is None:
            prompt = input_data.get("input", input_data.get("content", ""))
        if not isinstance(prompt, str) or not prompt:
            raise HTTPException(422, "agent node 输入必须提供 prompt 或 input/content")
        messages = [{"role": "system", "content": version.system_prompt}, {"role": "user", "content": prompt}]
        result = await self.gateway.generate(version.model_id, messages, session_id)
        usage = result.usage
        return {
            "content": result.content,
            "model_id": version.model_id,
            "agent_id": str(agent.id),
            "agent_version": version.version,
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
            },
        }
