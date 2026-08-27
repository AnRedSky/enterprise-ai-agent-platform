"""DAG Resume Frontier progression 适配模块。

职责：把当前 Multi-frontier Runtime 完成后的持久化事实重新交给唯一 DAG Planner，生成下一 Frontier 的确定性身份。
边界：不执行 Node、不写 Checkpoint、不获取 Worker ownership；持久化由现有 Frontier progression contract 负责。
关键依赖：WorkflowDagResumePlanner、WorkflowDagResumeRuntimePlan、WorkflowFrontierIdentity。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlan, WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan
from app.services.workflow.frontier import WorkflowFrontierIdentity


@dataclass(frozen=True)
class WorkflowDagNextFrontierPlan:
    """当前 Frontier 完成后下一 Frontier 的确定性规划结果。"""

    resume_plan: WorkflowDagResumePlan
    identity: WorkflowFrontierIdentity | None


class WorkflowDagFrontierProgressionService:
    """将 Durable Checkpoint 之后的完成事实收敛为下一 Frontier identity。"""

    @staticmethod
    def plan_next_frontier(
        *,
        definition: dict,
        execution_id: UUID,
        workflow_version_id: UUID,
        current_plan: WorkflowDagResumeRuntimePlan,
        completed_node_ids: set[str] | frozenset[str],
        state_data_by_node: dict[str, dict],
    ) -> WorkflowDagNextFrontierPlan:
        """根据当前 Frontier 完成后的持久化事实生成下一 Frontier。

        Args:
            definition: 固定 Workflow Version 的 DAG Definition。
            execution_id: 当前 Workflow Execution ID。
            workflow_version_id: 当前 Workflow Version ID。
            current_plan: 已成功执行并完成 Checkpoint 的当前 Runtime Plan。
            completed_node_ids: 写入当前 Branch Node Checkpoint 后的完整完成事实集合。
            state_data_by_node: 当前 Execution 可用于条件求值的已完成 Node state。

        Returns:
            下一 Frontier 的 Planner 结果与确定性 identity；没有下一 Frontier 时 identity 为 None。

        Raises:
            ValueError: 当前 frontier 未完整包含在 completed facts、state 数据非法或 Planner 无法生成合法下一 Frontier。

        设计意图：Checkpoint 之后必须重新运行唯一 Planner，而不能从当前 frontier 直接猜测后继 Node；这样才能让条件分支、Join 与 decision fingerprint 继续使用同一个正式规则入口。
        """
        if not current_plan.frontier_node_ids:
            raise ValueError("当前 Runtime Plan 必须至少包含一个 frontier")
        completed = set(completed_node_ids)
        missing_current = set(current_plan.frontier_node_ids) - completed
        if missing_current:
            raise ValueError(f"当前 frontier 尚未全部形成 completed durable facts: {sorted(missing_current)[0]}")
        if not isinstance(state_data_by_node, dict):
            raise ValueError("下一 Frontier planning 的 state_data_by_node 必须为对象")
        unknown_state = set(state_data_by_node) - completed
        if unknown_state:
            raise ValueError(f"state_data_by_node 存在未完成 Node: {sorted(unknown_state)[0]}")

        resume_plan = WorkflowDagResumePlanner.plan(
            definition=definition,
            completed_node_ids=frozenset(completed),
            state_data_by_node=state_data_by_node,
        )
        if not resume_plan.frontier_node_ids:
            return WorkflowDagNextFrontierPlan(resume_plan=resume_plan, identity=None)

        node_ids = {
            node.get("id")
            for node in definition.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        unknown_frontier = set(resume_plan.frontier_node_ids) - node_ids
        if unknown_frontier:
            raise ValueError(f"下一 Frontier 引用了未知 Node: {sorted(unknown_frontier)[0]}")

        identity = WorkflowFrontierIdentity(
            execution_id=execution_id,
            workflow_version_id=workflow_version_id,
            decision_fingerprint=resume_plan.decision_fingerprint,
            node_ids=resume_plan.frontier_node_ids,
        )
        return WorkflowDagNextFrontierPlan(resume_plan=resume_plan, identity=identity)
