"""Workflow DAG Resume Runtime 顺序规划模块。

职责：把只有单一 frontier 的 DAG Resume 计划展开为现有顺序 Runtime 可以消费的确定性 Node 序列。
边界：只做纯内存拓扑规划，不读取数据库、不执行 Node、不修改 Checkpoint、不合并分支状态。
关键依赖：WorkflowDagResumePlanner、WorkflowDagResumeRuntimePlanner；Multi-frontier 执行必须由专用 Executor 负责。
"""

from __future__ import annotations

from copy import deepcopy

from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
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
        state_data_by_node: dict | None = None,
    ) -> tuple[WorkflowDagResumeRuntimePlan, ...]:
        """生成当前 DAG 可以安全交给顺序 Runtime 的单 Node 计划序列。

        Args:
            definition: 固定 Workflow Version 的 DAG Definition。
            completed_node_ids: 已由调用方确认完成的持久化 Node ID 集合。
            state_data: 最新 Checkpoint 的状态快照。
            state_data_by_node: 已完成 Node 的持久化输出；存在条件边时必须提供。

        Returns:
            按 DAG frontier 逐步推进得到的确定性单 Node 计划；全部 Node 已完成时返回空元组。

        Raises:
            ValueError: 当前 frontier 同时包含多个 Node，表示必须进入 Multi-frontier Executor；或输入状态非法。

        设计边界：先由纯 Planner 决定 frontier，再把同一个不可变 Resume Plan 交给 Runtime Planner，避免一次解析产生两次 Decision。
        遇到条件边产生的 frontier 后立即停止线性展开，因为后续节点属于该 Branch 的下一次 Runtime 推进，不能在同一次顺序计划中预先选择。
        """
        if not isinstance(state_data, dict):
            raise ValueError("DAG Resume Runtime Sequence state_data 必须为对象")

        completed = set(completed_node_ids)
        node_ids = {
            node.get("id") for node in definition.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        node_state = deepcopy(state_data_by_node) if state_data_by_node is not None else None
        plans: list[WorkflowDagResumeRuntimePlan] = []
        while len(completed) < len(node_ids):
            resume_plan = WorkflowDagResumePlanner.plan(
                definition=definition,
                completed_node_ids=completed,
                state_data_by_node=node_state,
            )
            if len(resume_plan.frontier_node_ids) != 1:
                raise ValueError("DAG Resume Runtime 存在多个 frontier，必须交给 Multi-frontier Executor 执行")

            runtime_plan = WorkflowDagResumeRuntimePlanner.plan(
                definition=definition,
                completed_node_ids=completed,
                state_data=state_data,
                state_data_by_node=node_state,
                resume_plan=resume_plan,
            )
            node_id = runtime_plan.frontier_node_ids[0]
            plans.append(runtime_plan)
            completed.add(node_id)

            # 条件边已经完成一次不可逆的 Branch Decision；顺序 Planner 只负责把当前
            # Branch 的首个 frontier 交给 Runtime，不预先执行该 Branch 的后续 Node。
            conditional_frontier = any(
                edge.get("source") in completed
                and (edge.get("condition") is not None or edge.get("default") is True)
                and edge.get("target") == node_id
                for edge in definition.get("edges", [])
                if isinstance(edge, dict)
            )
            if conditional_frontier:
                break
        return tuple(plans)
