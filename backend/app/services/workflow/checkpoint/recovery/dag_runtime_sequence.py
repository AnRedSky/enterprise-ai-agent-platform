"""Workflow DAG Resume Runtime 顺序规划模块。

职责：把只有单一 frontier 的 DAG Resume 计划展开为现有顺序 Runtime 可以消费的确定性 Node 序列。
边界：只做纯内存拓扑规划，不读取数据库、不执行 Node、不修改 Checkpoint、不合并分支状态。
关键依赖：WorkflowDagResumeRuntimePlanner；Multi-frontier 执行必须由 WorkflowDagMultiFrontierExecutor 负责，不能在这里退化为共享状态的顺序执行。
"""

from __future__ import annotations

from copy import deepcopy

from app.services.workflow.checkpoint.recovery.dag_runtime import (
    WorkflowDagResumeRuntimePlan,
    WorkflowDagResumeRuntimePlanner,
)


class WorkflowDagResumeRuntimeSequencePlanner:
    """在单 frontier 场景下生成安全的线性 Node 计划。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        completed_node_ids: set[str] | frozenset[str],
        state_data: dict,
    ) -> tuple[WorkflowDagResumeRuntimePlan, ...]:
        """生成当前 DAG 可以安全交给顺序 Runtime 的单 frontier Node 计划序列。

        Args:
            definition: 固定 Workflow Version 的 DAG Definition。
            completed_node_ids: 已由调用方确认完成的持久化 Node ID 集合。
            state_data: 最新 Checkpoint 的状态快照。

        Returns:
            按 DAG frontier 逐步推进得到的确定性单 Node 计划；全部 Node 已完成时返回空元组。

        Raises:
            ValueError: 当前 frontier 同时包含多个 Node，表示必须进入 Multi-frontier Executor；或输入状态非法。

        设计边界：顺序规划器绝不把多个 Branch 强行压成一条线，也不把合并后的状态复制给不同 Branch。
        这样可以避免旧 Runtime 在拓扑上“看似支持 DAG”、实际上破坏 Branch state 隔离。Multi-frontier
        必须由专用 Executor 负责 Branch 执行、Checkpoint 与 Join readiness。
        """
        completed = set(completed_node_ids)
        node_ids = {
            node.get("id") for node in definition.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        plans: list[WorkflowDagResumeRuntimePlan] = []
        while len(completed) < len(node_ids):
            frontier_plan = WorkflowDagResumeRuntimePlanner.plan(
                definition=definition,
                completed_node_ids=completed,
                state_data=state_data,
            )
            if len(frontier_plan.frontier_node_ids) != 1:
                raise ValueError("DAG Resume Runtime 存在多个 frontier，必须交给 Multi-frontier Executor 执行")
            node_id = frontier_plan.frontier_node_ids[0]
            plans.append(
                WorkflowDagResumeRuntimePlan(
                    completed_node_ids=frontier_plan.completed_node_ids,
                    frontier_node_ids=(node_id,),
                    nodes=(deepcopy(frontier_plan.nodes[0]),),
                    state_data=deepcopy(frontier_plan.state_data),
                )
            )
            completed.add(node_id)
        return tuple(plans)
