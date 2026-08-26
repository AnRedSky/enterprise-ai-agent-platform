"""Workflow DAG Resume Runtime 顺序规划模块。

职责：把每次只有一个 frontier 的 DAG Resume 计划展开为可交给现有顺序 Runtime 的确定性 Node 序列。
边界：只做纯内存拓扑规划，不读取数据库、不执行 Node、不修改 Checkpoint，也不合并分支状态。
关键依赖：WorkflowDagResumeRuntimePlanner；调用方仍负责在每个 Node 成功后使用新的状态重新计算真实 Runtime 数据。
"""

from __future__ import annotations

from copy import deepcopy

from app.services.workflow.checkpoint.recovery.dag_runtime import (
    WorkflowDagResumeRuntimePlan,
    WorkflowDagResumeRuntimePlanner,
)


class WorkflowDagResumeRuntimeSequencePlanner:
    """在没有分支 frontier 时，将 DAG Resume 展开为安全的线性 Node 计划。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        completed_node_ids: set[str] | frozenset[str],
        state_data: dict,
    ) -> tuple[WorkflowDagResumeRuntimePlan, ...]:
        """生成当前 DAG 可以安全交给顺序 Runtime 的 Node 计划序列。

        Args:
            definition: 固定 Workflow Version 的 DAG Definition。
            completed_node_ids: 已由调用方确认完成的持久化 Node ID 集合。
            state_data: 最新 Checkpoint 的状态快照。

        Returns:
            按 DAG frontier 逐步推进得到的确定性单 Node 计划；全部 Node 已完成时返回空元组。

        Raises:
            ValueError: 任一步骤出现多个 frontier，表示存在尚未冻结的分支状态合并语义。

        设计边界：该规划器只模拟“完成当前 frontier”来确定拓扑顺序，不模拟 Node 输出或 state merge。
        因此实际执行时每个 Node 都必须使用 Runtime 当前状态，不能把这里的初始 `state_data` 当作所有
        后续 Node 的输入。
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
                raise ValueError(
                    "DAG Resume Runtime 当前无法展开为线性 Node 序列，多个 frontier 需要先冻结状态合并 Contract"
                )
            frontier_node_id = frontier_plan.frontier_node_ids[0]
            node = next(
                node for node in definition["nodes"]
                if isinstance(node, dict) and node.get("id") == frontier_node_id
            )
            plans.append(
                WorkflowDagResumeRuntimePlan(
                    completed_node_ids=frontier_plan.completed_node_ids,
                    frontier_node_id=frontier_node_id,
                    node=deepcopy(node),
                    state_data=deepcopy(state_data),
                )
            )
            completed.add(frontier_node_id)
        return tuple(plans)
