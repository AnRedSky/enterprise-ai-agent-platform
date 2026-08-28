"""Delegation Worker Runtime Bridge。

职责：把已 Claim 的 AgentDelegation 映射到现有 Workflow Worker Runtime，并显式装配目标 Agent version、model profile、任务输入、context refs、tool refs 与 trace identity。
边界：不创建新的 Worker、Lease、Retry、Recovery 或 Provider；目标 Agent 必须复用既有发布版本与 WorkflowRuntime。
关键依赖：AgentDelegation、Agent/AgentVersion、WorkflowVersion、SQLAlchemy AsyncSession。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_delegation import AgentDelegation
from app.models.core import Agent, AgentVersion, User


@dataclass(frozen=True)
class DelegationRuntimeContext:
    """已 Claim Delegation 的不可变 Runtime 上下文。"""

    delegation_id: UUID
    target_agent_version_id: UUID
    target_agent_id: UUID
    model_profile_id: UUID | None
    input_data: dict
    selected_context_refs: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    trace_id: str
    prompt: str
    timeout_at: datetime | None


class AgentDelegationRuntimeBridge:
    """Delegation 到既有 WorkflowRuntime 的唯一执行桥接入口。"""

    @staticmethod
    def _resolve_prompt(input_data: dict) -> str:
        """把显式 Delegation 输入转换为 Agent Runtime prompt，不读取父 Execution 私有状态。"""
        for key in ("prompt", "input", "content"):
            value = input_data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return json.dumps(input_data, ensure_ascii=False, sort_keys=True)

    @classmethod
    async def load(cls, db: AsyncSession, execution) -> DelegationRuntimeContext | None:
        """从 Worker Execution 反查已 Claim Delegation，并校验 tenant 与发布版本边界。"""
        delegation = (
            await db.execute(
                select(AgentDelegation).where(
                    AgentDelegation.worker_execution_id == execution.id,
                    AgentDelegation.tenant_id == execution.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if delegation is None:
            return None
        if delegation.status != "running":
            raise HTTPException(409, f"Delegation 当前状态为 {delegation.status}，不允许进入 Worker Runtime")

        result = await db.execute(
            select(AgentVersion, Agent).join(Agent, Agent.id == AgentVersion.agent_id).join(User, User.id == Agent.owner_id).where(
                AgentVersion.id == delegation.target_agent_version_id,
                AgentVersion.agent_id == Agent.id,
                Agent.published_version_id == AgentVersion.id,
                Agent.status == "published",
                User.tenant_id == execution.tenant_id,
            )
        )
        row = result.first()
        if row is None:
            raise HTTPException(409, "Delegation target Agent version 不存在、跨 tenant 或已不是发布版本")
        target_version, target_agent = row
        if target_version.model_profile_id != delegation.model_profile_id:
            raise HTTPException(409, "Delegation model profile 与目标 Agent version 不一致")

        input_data = dict(delegation.input_data or {})
        return DelegationRuntimeContext(
            delegation_id=delegation.id,
            target_agent_version_id=target_version.id,
            target_agent_id=target_agent.id,
            model_profile_id=target_version.model_profile_id,
            input_data=input_data,
            selected_context_refs=tuple(delegation.selected_context_refs or []),
            allowed_tools=tuple(delegation.allowed_tools or []),
            trace_id=delegation.trace_id,
            prompt=cls._resolve_prompt(input_data),
            timeout_at=delegation.timeout_at,
        )

    @staticmethod
    def build_runtime_version(parent_version, context: DelegationRuntimeContext):
        """构造仅用于本次 Worker 执行的内存 Runtime Version。"""
        definition = parent_version.definition if isinstance(parent_version.definition, dict) else {}
        runtime_config = dict(definition.get("config") or {})
        runtime_config["delegation_context"] = {
            "delegation_id": str(context.delegation_id),
            "target_agent_version_id": str(context.target_agent_version_id),
            "model_profile_id": str(context.model_profile_id) if context.model_profile_id else None,
            "selected_context_refs": list(context.selected_context_refs),
            "allowed_tools": list(context.allowed_tools),
            "trace_id": context.trace_id,
        }
        node = {
            "id": "delegation.target",
            "type": "agent",
            "config": {
                "agent_id": str(context.target_agent_id),
                "prompt": context.prompt,
                "delegation_context": runtime_config["delegation_context"],
            },
        }
        # Delegation produces a single synthetic agent node, not a persisted DAG.
        # Omit ``edges`` because the DAG validator requires non-empty edges whenever
        # the key exists; adding a synthetic edge would alter execution semantics.
        return SimpleNamespace(
            id=parent_version.id,
            workflow_id=parent_version.workflow_id,
            version=parent_version.version,
            definition={"config": runtime_config, "nodes": [node]},
            status=parent_version.status,
            created_by=parent_version.created_by,
        )
