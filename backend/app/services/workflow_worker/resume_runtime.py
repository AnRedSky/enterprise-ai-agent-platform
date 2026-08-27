"""Durable Workflow Runtime Resume 适配层。

职责：在进入唯一 WorkflowRuntime 前，根据当前 Execution 的 durable Node facts
过滤已经成功完成的线性节点，避免 Worker Retry / Lease Recovery 重复执行已成功节点。
边界：DAG 继续交给 WorkflowRuntime 内置 Planner/Executor；本模块不复制 DAG 规划、Node Runtime
或 Checkpoint 算法。
"""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import select

from app.models.workflow_execution import WorkflowNodeExecution
from app.runtime.workflow import WorkflowRuntime


class DurableResumeWorkflowRuntime(WorkflowRuntime):
    """仅补充线性 Workflow 的 durable Node resume 入口。"""

    async def _resume_version(self, execution, version):
        definition = version.definition if isinstance(version.definition, dict) else {}
        edges = definition.get("edges") or []
        if edges:
            return version

        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowNodeExecution.tenant_id == execution.tenant_id,
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
        definition = version.definition if isinstance(version.definition, dict) else {}
        nodes = definition.get("nodes") or []
        if not nodes or definition.get("edges"):
            return False
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowNodeExecution.tenant_id == execution.tenant_id,
                WorkflowNodeExecution.status == "completed",
            )
            .order_by(WorkflowNodeExecution.created_at.desc(), WorkflowNodeExecution.id.desc())
        )
        completed = list(result.scalars().all())
        if {node.node_id for node in completed} >= {node["id"] for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}:
            final_data = dict(completed[0].output_data or {}) if completed else dict(execution.input_data or {})
            await self.execution_service.transition(execution, "completed", output_data=final_data, actor_id=actor_id)
            return True
        return False

    async def execute(self, execution, version, actor_id, is_admin=False, allow_legacy_empty_nodes=False):
        if await self._complete_if_all_nodes_resumed(execution, version, actor_id):
            return dict(execution.output_data or execution.input_data or {})
        resumed_version = await self._resume_version(execution, version)
        if isinstance(resumed_version.definition, dict) and not (resumed_version.definition.get("nodes") or []):
            return dict(execution.output_data or execution.input_data or {})
        return await super().execute(
            execution,
            resumed_version,
            actor_id,
            is_admin=is_admin,
            allow_legacy_empty_nodes=allow_legacy_empty_nodes,
        )
