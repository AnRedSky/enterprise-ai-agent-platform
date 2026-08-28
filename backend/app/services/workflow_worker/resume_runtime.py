"""Durable Workflow Runtime Resume 适配层。

职责：在进入唯一 WorkflowRuntime 前，根据当前 Execution 的 durable Node facts
过滤已经成功完成的线性节点，并恢复持久化的 Node / Workflow Retry budget。
边界：DAG 继续交给 WorkflowRuntime 内置 Planner/Executor；本模块不复制 DAG 规划、Node Runtime
或 Checkpoint 算法。
"""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select

from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.runtime.workflow import WorkflowRuntime


class DurableResumeWorkflowRuntime(WorkflowRuntime):
    """补充线性 Workflow 的 durable Node resume 与持久化 Retry budget 入口。"""

    async def _load_persisted_retry_count(self, execution) -> int:
        """读取当前 Execution 已消耗的持久化 Node Retry 次数。

        Args:
            execution: 当前 Workflow Execution。

        Returns:
            所有 Node 已持久化消耗的 Retry 次数总和。

        说明：Node `attempt` 从 1 开始，只有 failed → running 的重试会递增；因此
        `attempt - 1` 是跨 Worker Recovery 后仍然有效的 Retry 消耗量。
        """
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .join(WorkflowExecution, WorkflowExecution.id == WorkflowNodeExecution.execution_id)
            .where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowExecution.tenant_id == execution.tenant_id,
            )
        )
        return sum(max(0, int(node.attempt or 1) - 1) for node in result.scalars().all())

    async def _execute_node_with_policy(self, service, execution, node, current_data, actor_id,
                                        is_admin, workflow_timeout, max_retries, started,
                                        workflow_retry_counter):
        """恢复 Node 的持久化 attempt，并把本轮 Retry 上限收敛到剩余 budget。

        Args:
            service: Workflow Execution Service。
            execution: 当前 Workflow Execution。
            node: 待执行 Node Definition。
            current_data: 当前 Node 输入状态。
            actor_id: 执行操作者。
            is_admin: 是否使用管理员执行权限。
            workflow_timeout: Workflow 总超时时间，单位毫秒。
            max_retries: 当前 Runtime 可使用的 Workflow Retry budget。
            started: Runtime 开始时间。
            workflow_retry_counter: 当前 Runtime 已消耗的 Retry 计数器。

        Returns:
            Node 执行后的状态数据。

        Raises:
            HTTPException: 持久化 Node attempt 已耗尽时拒绝再次执行。
        """
        policy = self.resolve_retry_policy(node["config"])
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .join(WorkflowExecution, WorkflowExecution.id == WorkflowNodeExecution.execution_id)
            .where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowExecution.tenant_id == execution.tenant_id,
                WorkflowNodeExecution.node_id == node["id"],
            )
        )
        persisted = result.scalar_one_or_none()
        if persisted is not None and persisted.status == "failed":
            remaining_attempts = policy["max_attempts"] - int(persisted.attempt or 1)
            if remaining_attempts <= 0:
                raise HTTPException(500, f"Workflow Node {node['id']} Retry 次数已耗尽")
            resumed_node = dict(node)
            resumed_config = dict(node["config"])
            resumed_retry = dict(resumed_config.get("retry") or {})
            resumed_retry["max_attempts"] = remaining_attempts
            resumed_config["retry"] = resumed_retry
            resumed_node["config"] = resumed_config
            node = resumed_node
        return await super()._execute_node_with_policy(
            service,
            execution,
            node,
            current_data,
            actor_id,
            is_admin,
            workflow_timeout,
            max_retries,
            started,
            workflow_retry_counter,
        )

    async def execute(self, execution, version, actor_id, is_admin=False, allow_legacy_empty_nodes=False):
        """执行 Resume Runtime，并从 durable Node facts 恢复 Workflow Retry budget。

        Args:
            execution: 当前 Workflow Execution。
            version: 已发布 Workflow Version。
            actor_id: 执行操作者。
            is_admin: 是否使用管理员执行权限。
            allow_legacy_empty_nodes: 是否允许历史空节点定义。

        Returns:
            Workflow Runtime 最终输出状态。

        说明：Workflow Retry budget 与 Node attempt 均属于持久化执行事实，Worker Recovery
        不能把本地计数器清零，否则会绕过原配置的 Retry 上限。
        """
        persisted_retry_count = await self._load_persisted_retry_count(execution)
        definition = version.definition if isinstance(version.definition, dict) else {}
        runtime_config = dict(definition.get("config") or {})
        retry_budget = dict(runtime_config.get("retry_budget") or {})
        configured_max_retries = int(retry_budget.get("max_retries", 0))
        retry_budget["max_retries"] = max(0, configured_max_retries - persisted_retry_count)
        runtime_config["retry_budget"] = retry_budget
        resumed_definition = dict(definition)
        resumed_definition["config"] = runtime_config
        resumed_version = SimpleNamespace(
            id=version.id,
            workflow_id=version.workflow_id,
            version=version.version,
            definition=resumed_definition,
            status=version.status,
            created_by=version.created_by,
        )
        if await self._complete_if_all_nodes_resumed(execution, resumed_version, actor_id):
            return dict(getattr(execution, "output_data", None) or {})
        resumed_version = await self._resume_version(execution, resumed_version)
        return await super().execute(
            execution,
            resumed_version,
            actor_id,
            is_admin=is_admin,
            allow_legacy_empty_nodes=allow_legacy_empty_nodes,
        )

    async def _resume_version(self, execution, version):
        """根据 durable Node facts 过滤已完成的线性节点，DAG 仍由既有 Planner 负责。"""
        definition = version.definition if isinstance(version.definition, dict) else {}
        edges = definition.get("edges") or []
        if edges:
            return version

        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .join(WorkflowExecution, WorkflowExecution.id == WorkflowNodeExecution.execution_id)
            .where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowExecution.tenant_id == execution.tenant_id,
                WorkflowNodeExecution.status == "completed",
            )
        )
        completed_ids = {node.node_id for node in result.scalars().all()}
        if not completed_ids:
            return version

        nodes = definition.get("nodes") or []
        remaining_nodes = [node for node in nodes if isinstance(node, dict) and node.get("id") not in completed_ids]
        if len(remaining_nodes) == len(nodes):
            return version

        resumed_definition = dict(definition)
        resumed_definition["nodes"] = remaining_nodes
        return SimpleNamespace(
            id=version.id,
            workflow_id=version.workflow_id,
            version=version.version,
            definition=resumed_definition,
            status=version.status,
            created_by=version.created_by,
        )

    async def _complete_if_all_nodes_resumed(self, execution, version, actor_id):
        """检查线性 Workflow 是否已经全部完成，避免 Recovery 后再次执行全部节点。"""
        definition = version.definition if isinstance(version.definition, dict) else {}
        nodes = definition.get("nodes") or []
        if not nodes or definition.get("edges"):
            return False
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .join(WorkflowExecution, WorkflowExecution.id == WorkflowNodeExecution.execution_id)
            .where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowExecution.tenant_id == execution.tenant_id,
                WorkflowNodeExecution.status == "completed",
            )
            .order_by(WorkflowNodeExecution.created_at.desc(), WorkflowNodeExecution.id.desc())
        )
        completed = list(result.scalars().all())
        if {node.node_id for node in completed} >= {node["id"] for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}:
            final_data = dict(completed[0].output_data or {}) if completed else dict(execution.input_data or {})
            execution.output_data = final_data
            await self.execution_service.transition(execution, "completed", output_data=final_data, actor_id=actor_id)
            return True
        return False
