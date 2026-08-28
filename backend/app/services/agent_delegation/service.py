"""Agent Delegation Domain Service。

职责：创建并管理受治理 Delegation，统一执行 tenant、Agent version、权限、幂等、深度、并发与生命周期规则。
边界：不启动 Worker，不实现独立 retry/recovery 状态机；Worker Runtime 后续只调用本服务的正式入口。
关键依赖：WorkflowExecution、Agent/AgentVersion/User、AgentDelegationRepository、AuditLog 与 WorkflowTraceEvent。
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.agent_delegation import AgentDelegation
from app.models.core import Agent, AgentVersion, AuditLog, User, utcnow_naive
from app.models.workflow import WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.agent_delegation.identity import delegation_identity_key, validate_budget
from app.services.agent_delegation.repository import AgentDelegationRepository


class AgentDelegationService:
    """Agent Delegation 的唯一领域服务入口。"""

    TERMINAL_STATES = {"completed", "failed", "timed_out", "cancelled"}
    TRANSITIONS = {
        "pending": {"running", "cancelled"},
        "running": {"completed", "failed", "timed_out", "cancelled"},
        "completed": set(),
        "failed": set(),
        "timed_out": set(),
        "cancelled": set(),
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AgentDelegationRepository(db)

    @staticmethod
    def _defaults() -> tuple[int, int, int, dict]:
        """读取企业治理默认预算；默认值来自配置，不写入业务流程。"""
        return (
            settings.multi_agent_max_delegation_depth,
            settings.multi_agent_max_active_delegations,
            settings.multi_agent_timeout_seconds,
            dict(settings.multi_agent_model_budget),
        )

    async def _source_agent_version(self, execution: WorkflowExecution, actor_id: UUID, admin: bool = False) -> AgentVersion:
        """从当前 Execution 的 Workflow Definition 确定 Orchestrator Agent version。"""
        version = (await self.db.execute(select(WorkflowVersion).where(WorkflowVersion.id == execution.workflow_version_id))).scalar_one_or_none()
        if version is None:
            raise HTTPException(409, "Workflow Execution 版本不存在")
        definition = version.definition if isinstance(version.definition, dict) else {}
        nodes = definition.get("nodes") or []
        selected = None
        if execution.current_node_id:
            selected = next((item for item in nodes if isinstance(item, dict) and item.get("id") == execution.current_node_id), None)
        if selected is None:
            selected = next((item for item in nodes if isinstance(item, dict) and item.get("type") == "agent"), None)
        if not selected or selected.get("type") != "agent":
            raise HTTPException(409, "当前 Execution 没有可作为 Orchestrator 的 Agent Node")
        try:
            agent_id = UUID(str((selected.get("config") or {}).get("agent_id")))
        except (ValueError, TypeError) as exc:
            raise HTTPException(409, "Orchestrator Agent Node 缺少有效 agent_id") from exc
        result = await self.db.execute(select(AgentVersion).join(Agent, Agent.id == AgentVersion.agent_id).join(User, User.id == Agent.owner_id).where(
            AgentVersion.id == Agent.published_version_id,
            Agent.id == agent_id,
            User.tenant_id == execution.tenant_id,
            Agent.status == "published",
        ))
        source_version = result.scalar_one_or_none()
        if source_version is None:
            raise HTTPException(409, "Orchestrator Agent 尚未发布可运行版本")
        if not admin and actor_id != execution.created_by:
            raise HTTPException(403, "无权从当前 Workflow Execution 委派 Agent 子任务")
        return source_version

    async def _target_version(self, *, tenant_id: UUID, target_agent_version_id: UUID) -> AgentVersion:
        """读取并校验目标 Agent version 的 tenant 与 published lineage。"""
        result = await self.db.execute(select(AgentVersion).join(Agent, Agent.id == AgentVersion.agent_id).join(User, User.id == Agent.owner_id).where(
            AgentVersion.id == target_agent_version_id,
            User.tenant_id == tenant_id,
            Agent.status == "published",
            Agent.published_version_id == target_agent_version_id,
        ))
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(409, "Target Agent version 不存在、跨 tenant 或尚未发布")
        return target

    async def _delegation_depth(self, *, tenant_id: UUID, source_execution_id: UUID) -> int:
        """沿 worker_execution lineage 计算委派深度，缺少父 Delegation 时视为根委派。"""
        depth = 1
        current_execution_id = source_execution_id
        visited: set[UUID] = set()
        while current_execution_id not in visited:
            visited.add(current_execution_id)
            result = await self.db.execute(select(AgentDelegation).where(
                AgentDelegation.tenant_id == tenant_id,
                AgentDelegation.worker_execution_id == current_execution_id,
            ).limit(1))
            parent = result.scalar_one_or_none()
            if parent is None:
                return depth
            depth += 1
            current_execution_id = parent.source_execution_id
            if depth > settings.multi_agent_max_delegation_depth + 1:
                return depth
        raise HTTPException(409, "检测到 Delegation lineage 环路")

    async def create(
        self,
        *,
        tenant_id: UUID,
        source_execution_id: UUID,
        actor_id: UUID,
        target_agent_version_id: UUID,
        delegation_key: str,
        input_data: dict,
        selected_context_refs: list[str],
        allowed_tools: list[str],
        max_delegation_depth: int | None = None,
        max_active_delegations: int | None = None,
        timeout_seconds: int | None = None,
        model_budget: dict | None = None,
        admin: bool = False,
    ) -> AgentDelegation:
        """创建 tenant-scoped Delegation，并以数据库唯一约束保证并发幂等。"""
        # 创建前锁住父 Execution，使活动 Delegation 计数与创建动作形成同一串行化边界；否则两个并发请求可能同时看到相同 active_count，从而突破 max_active_delegations。
        source = (await self.db.execute(select(WorkflowExecution).where(
            WorkflowExecution.id == source_execution_id,
            WorkflowExecution.tenant_id == tenant_id,
        ).with_for_update())).scalar_one_or_none()
        if source is None:
            raise HTTPException(404, "Workflow Execution 不存在")
        if source.status in {"completed", "failed", "cancelled"}:
            raise HTTPException(409, "终态 Execution 不允许创建 Delegation")
        if not admin and actor_id != source.created_by:
            raise HTTPException(403, "无权从当前 Workflow Execution 创建 Delegation")

        defaults = self._defaults()
        max_depth, max_active, timeout, normalized_model_budget = validate_budget(
            max_delegation_depth=defaults[0] if max_delegation_depth is None else max_delegation_depth,
            max_active_delegations=defaults[1] if max_active_delegations is None else max_active_delegations,
            timeout_seconds=defaults[2] if timeout_seconds is None else timeout_seconds,
            model_budget=defaults[3] if model_budget is None else model_budget,
        )
        if not isinstance(input_data, dict) or len(input_data) > 100:
            raise HTTPException(422, "input_data 必须为对象且字段数量不超过 100")
        if any(not isinstance(item, str) or not item or len(item) > 256 for item in selected_context_refs):
            raise HTTPException(422, "selected_context_refs 包含无效引用")
        if any(not isinstance(item, str) or not item or len(item) > 128 for item in allowed_tools):
            raise HTTPException(422, "allowed_tools 包含无效工具标识")
        normalized_key = delegation_key.strip()
        delegation_identity_key(tenant_id=tenant_id, source_execution_id=source_execution_id, delegation_key=normalized_key)

        existing = await self.repository.get_by_key(tenant_id=tenant_id, source_execution_id=source_execution_id, delegation_key=normalized_key)
        if existing is not None:
            if existing.target_agent_version_id != target_agent_version_id:
                raise HTTPException(409, "delegation_key 已绑定其他 target Agent version")
            return existing
        source_version = await self._source_agent_version(source, actor_id, admin=admin)
        target_version = await self._target_version(tenant_id=tenant_id, target_agent_version_id=target_agent_version_id)
        depth = await self._delegation_depth(tenant_id=tenant_id, source_execution_id=source_execution_id)
        if depth > max_depth:
            raise HTTPException(409, "Delegation depth 已达到治理上限")
        active_count = await self.repository.count_active(tenant_id=tenant_id, source_execution_id=source_execution_id)
        if active_count >= max_active:
            raise HTTPException(409, "当前 Execution 活动 Delegation 已达到治理上限")

        now = utcnow_naive()
        item = AgentDelegation(
            tenant_id=tenant_id,
            source_execution_id=source_execution_id,
            source_agent_version_id=source_version.id,
            target_agent_version_id=target_version.id,
            delegation_key=normalized_key,
            status="pending",
            input_data=dict(input_data),
            selected_context_refs=list(selected_context_refs),
            allowed_tools=list(allowed_tools),
            model_profile_id=target_version.model_profile_id,
            model_budget=normalized_model_budget,
            max_delegation_depth=max_depth,
            max_active_delegations=max_active,
            timeout_seconds=timeout,
            depth=depth,
            trace_id=str(source_execution_id),
            timeout_at=now + timedelta(seconds=timeout),
        )
        self.db.add(item)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.repository.get_by_key(tenant_id=tenant_id, source_execution_id=source_execution_id, delegation_key=normalized_key)
            if existing is None:
                raise
            if existing.target_agent_version_id != target_agent_version_id:
                raise HTTPException(409, "delegation_key 已绑定其他 target Agent version")
            return existing
        self.db.add(AuditLog(
            actor_id=actor_id, tenant_id=tenant_id, workflow_id=source.workflow_id, workflow_version_id=source.workflow_version_id,
            workflow_execution_id=source.id, action="workflow.delegation.created", resource_type="agent_delegation", resource_id=str(item.id),
            trace_id=item.trace_id, status="success", metadata_json={"target_agent_version_id": str(target_version.id), "depth": depth},
        ))
        self.db.add(WorkflowTraceEvent(
            tenant_id=tenant_id, execution_id=source.id, workflow_id=source.workflow_id, workflow_version_id=source.workflow_version_id,
            event_type="agent.delegation.created", status="pending", trace_id=item.trace_id, actor_id=actor_id,
            data={"delegation_id": str(item.id), "source_agent_version_id": str(source_version.id), "target_agent_version_id": str(target_version.id), "depth": depth},
        ))
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list(self, *, tenant_id: UUID, source_execution_id: UUID, actor_id: UUID, admin: bool) -> list[AgentDelegation]:
        """查询来源 Execution 的 Delegation，并复用现有 Execution 权限边界。"""
        source = (await self.db.execute(select(WorkflowExecution).where(
            WorkflowExecution.id == source_execution_id, WorkflowExecution.tenant_id == tenant_id,
        ))).scalar_one_or_none()
        if source is None:
            raise HTTPException(404, "Workflow Execution 不存在")
        if not admin and source.created_by != actor_id:
            raise HTTPException(403, "无权查询当前 Workflow Execution 的 Delegation")
        return await self.repository.list_by_source(tenant_id=tenant_id, source_execution_id=source_execution_id)

    async def get(self, *, tenant_id: UUID, source_execution_id: UUID, delegation_id: UUID, actor_id: UUID, admin: bool) -> AgentDelegation:
        """读取单个 Delegation，并强制 source Execution tenant/permission lineage。"""
        items = await self.list(tenant_id=tenant_id, source_execution_id=source_execution_id, actor_id=actor_id, admin=admin)
        item = next((candidate for candidate in items if candidate.id == delegation_id), None)
        if item is None:
            raise HTTPException(404, "Agent Delegation 不存在")
        return item

    async def cancel(self, *, tenant_id: UUID, source_execution_id: UUID, delegation_id: UUID, actor_id: UUID, admin: bool) -> AgentDelegation:
        """取消 pending/running Delegation；取消只改变 Delegation 自身，不直接终止父 Execution。"""
        item = await self.get(tenant_id=tenant_id, source_execution_id=source_execution_id, delegation_id=delegation_id, actor_id=actor_id, admin=admin)
        if "cancelled" not in self.TRANSITIONS[item.status]:
            raise HTTPException(409, f"Delegation 不允许从 {item.status} 转换到 cancelled")
        item.status = "cancelled"
        item.ended_at = utcnow_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item
