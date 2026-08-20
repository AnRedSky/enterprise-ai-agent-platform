from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion, User
from app.runtime.model_gateway import ModelGateway


class WorkflowRuntime:
    """Execute the stable Phase 1.5-D sequential workflow contract.

    Definition contract:
    {"nodes": [{"id": "...", "type": "input|agent|output", "config": {...}}],
     "config": {"timeout_ms": 30000}}
    Nodes execute in declaration order. Branching and parallel scheduling remain
    outside this phase and must not be inferred from arbitrary definition data.

    Node retry is opt-in. By default every node has exactly one attempt. When a
    retry policy is configured, only explicitly classified transient failures are
    retried, with bounded exponential backoff and jitter.
    """

    NODE_TYPES = {"input", "agent", "output"}
    DEFAULT_TIMEOUT_MS = 30_000
    MAX_TIMEOUT_MS = 300_000
    DEFAULT_RETRY_POLICY = {
        "max_attempts": 1,
        "backoff_ms": 250,
        "max_backoff_ms": 5_000,
        "jitter_ms": 250,
        "retryable_error_codes": [
            "NODE_TIMEOUT",
            "HTTP_429",
            "HTTP_502",
            "HTTP_503",
            "HTTP_504",
            "CONNECTION_ERROR",
        ],
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gateway = ModelGateway()

    @classmethod
    def validate_timeout_ms(cls, value: object, *, field: str = "timeout_ms") -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(422, f"{field} 必须为整数毫秒")
        if value <= 0 or value > cls.MAX_TIMEOUT_MS:
            raise HTTPException(422, f"{field} 必须在 1-{cls.MAX_TIMEOUT_MS} 毫秒范围内")
        return value

    @classmethod
    def resolve_timeout_ms(cls, config: dict | None, *, field: str = "timeout_ms") -> int:
        config = config or {}
        value = config.get(field, cls.DEFAULT_TIMEOUT_MS)
        return cls.validate_timeout_ms(value, field=field)

    @classmethod
    def resolve_retry_policy(cls, config: dict | None) -> dict:
        config = config or {}
        raw = config.get("retry") or {}
        if not isinstance(raw, dict):
            raise HTTPException(422, "retry config 必须为对象")
        policy = {**cls.DEFAULT_RETRY_POLICY, **raw}
        max_attempts = policy["max_attempts"]
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 5:
            raise HTTPException(422, "retry.max_attempts 必须在 1-5 范围内")
        for key, maximum in (("backoff_ms", 10_000), ("max_backoff_ms", 60_000), ("jitter_ms", 10_000)):
            value = policy[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
                raise HTTPException(422, f"retry.{key} 必须在 0-{maximum} 范围内")
        if policy["max_backoff_ms"] < policy["backoff_ms"]:
            raise HTTPException(422, "retry.max_backoff_ms 不能小于 retry.backoff_ms")
        codes = policy["retryable_error_codes"]
        if not isinstance(codes, list) or any(not isinstance(code, str) or not code for code in codes):
            raise HTTPException(422, "retry.retryable_error_codes 必须为非空字符串数组")
        if len(codes) > 20:
            raise HTTPException(422, "retry.retryable_error_codes 最多允许 20 项")
        return {
            "max_attempts": max_attempts,
            "backoff_ms": policy["backoff_ms"],
            "max_backoff_ms": policy["max_backoff_ms"],
            "jitter_ms": policy["jitter_ms"],
            "retryable_error_codes": list(dict.fromkeys(codes)),
        }

    @classmethod
    def classify_error(cls, exc: BaseException, *, workflow_timeout: bool = False) -> str:
        if workflow_timeout:
            return "WORKFLOW_TIMEOUT"
        if isinstance(exc, asyncio.TimeoutError):
            return "NODE_TIMEOUT"
        if isinstance(exc, HTTPException):
            return f"HTTP_{exc.status_code}"
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return "CONNECTION_ERROR" if isinstance(exc, ConnectionError) else "NODE_TIMEOUT"
        return type(exc).__name__

    @classmethod
    def retry_delay_seconds(cls, policy: dict, failed_attempt: int, random_value: float) -> float:
        ceiling_ms = min(policy["max_backoff_ms"], policy["backoff_ms"] * (2 ** max(failed_attempt - 1, 0)))
        jitter_ms = max(0.0, min(1.0, random_value)) * policy["jitter_ms"]
        return min(policy["max_backoff_ms"], ceiling_ms + jitter_ms) / 1000

    @classmethod
    def validate_definition(cls, definition: dict) -> list[dict]:
        if not isinstance(definition, dict):
            raise HTTPException(422, "Workflow definition 必须为对象")
        nodes = definition.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise HTTPException(422, "Workflow definition 必须包含非空 nodes")
        runtime_config = definition.get("config") or {}
        if not isinstance(runtime_config, dict):
            raise HTTPException(422, "Workflow config 必须为对象")
        cls.resolve_timeout_ms(runtime_config)
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
            config = raw.get("config") or {}
            if not isinstance(config, dict):
                raise HTTPException(422, f"Workflow node config 必须为对象: {node_id}")
            cls.resolve_timeout_ms(config)
            cls.resolve_retry_policy(config)
            seen.add(node_id)
            normalized.append({"id": node_id, "type": node_type, "config": config})
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
