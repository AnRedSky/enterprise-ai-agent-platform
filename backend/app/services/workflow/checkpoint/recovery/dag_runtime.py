"""Workflow DAG Resume Runtime 计划模块。

职责：把纯内存 DAG Resume Frontier 转换为 Runtime 可以消费的确定性多 Node 计划。
边界：不读取数据库、不创建 Node Execution、不修改 Checkpoint、不获取 Worker ownership；已完成 Node 事实及其分支状态必须由调用方从持久化来源提供。
关键依赖：WorkflowDagResumePlanner、WorkflowDagBranchStateMergeService；真正的 Node 执行仍由现有 WorkflowRuntime / Worker 负责。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_state_merge import (
    WorkflowDagBranchState,
    WorkflowDagBranchStateMergeService,
)


@dataclass(frozen=True)
class WorkflowDagResumeRuntimePlan:
    """DAG Resume Runtime 的确定性多 Node frontier 执行计划。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_ids: tuple[str, ...]
    nodes: tuple[dict, ...]
    state_data: dict

    @property
    def frontier_node_id(self) -> str:
        """兼容单 frontier 调用方；多 frontier 时显式拒绝隐式选择。"""
        if len(self.frontier_node_ids) != 1:
            raise ValueError("DAG Resume Runtime 存在多个 frontier，不能隐式选择单一 frontier Node")
        return self.frontier_node_ids[0]

    @property
    def node(self) -> dict:
        """兼容单 frontier 调用方；多 frontier 时使用 nodes。"""
        if len(self.nodes) != 1:
            raise ValueError("DAG Resume Runtime 存在多个 frontier，不能隐式选择单一 Node")
        return deepcopy(self.nodes[0])


class WorkflowDagResumeRuntimePlanner:
    """将 DAG Resume frontier 收敛为当前 Runtime 可安全消费的多节点计划。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        completed_node_ids: set[str] | frozenset[str],
        state_data: dict | None = None,
        branch_state_data: Mapping[str, Mapping[str, object]] | None = None,
    ) -> WorkflowDagResumeRuntimePlan:
        """生成当前 Runtime 可以执行的 DAG Resume frontier 计划。

        `state_data` 用于已有单 frontier Resume；当 frontier 超过一个 Node 时，调用方必须提供
        `branch_state_data`，其 key 必须覆盖所有 frontier Node，并且每个值都必须来自已经验证的持久化
        Checkpoint 分支快照。多分支状态统一交给 Branch State Merge Contract，禁止 Runtime 自行 last-write-wins。
        """
        if state_data is not None and not isinstance(state_data, dict):
            raise ValueError("DAG Resume Runtime state_data 必须为对象")
        if branch_state_data is not None and not isinstance(branch_state_data, Mapping):
            raise ValueError("DAG Resume Runtime branch_state_data 必须为对象")

        plan = WorkflowDagResumePlanner.plan(
            definition=definition,
            completed_node_ids=completed_node_ids,
        )
        node_by_id = {
            node["id"]: node
            for node in definition["nodes"]
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        frontier_node_ids = plan.frontier_node_ids
        nodes = tuple(deepcopy(node_by_id[node_id]) for node_id in frontier_node_ids)

        if len(frontier_node_ids) <= 1:
            if state_data is None:
                raise ValueError("DAG Resume Runtime 单 frontier 必须提供 state_data")
            merged_state_data = deepcopy(state_data)
        else:
            if branch_state_data is None:
                raise ValueError("DAG Resume Runtime 多 frontier 必须提供 branch_state_data")
            missing = [node_id for node_id in frontier_node_ids if node_id not in branch_state_data]
            unknown = [node_id for node_id in branch_state_data if node_id not in frontier_node_ids]
            if missing:
                raise ValueError(f"DAG Resume Runtime 缺少 frontier 分支状态: {missing[0]}")
            if unknown:
                raise ValueError(f"DAG Resume Runtime 存在非 frontier 分支状态: {unknown[0]}")

            merge_plan = WorkflowDagBranchStateMergeService.merge(
                branches=tuple(
                    WorkflowDagBranchState(node_id=node_id, state_data=branch_state_data[node_id])
                    for node_id in frontier_node_ids
                )
            )
            merged_state_data = merge_plan.state_data

        return WorkflowDagResumeRuntimePlan(
            completed_node_ids=plan.completed_node_ids,
            frontier_node_ids=frontier_node_ids,
            nodes=nodes,
            state_data=merged_state_data,
        )
