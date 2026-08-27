"""Workflow DAG Resume Runtime 计划模块。

职责：把纯内存 DAG Resume Frontier 转换为 Runtime 可以消费的确定性多 Node 计划，并保留条件边选中的 predecessor 与 decision fingerprint。
边界：不读取数据库、不创建 Node Execution、不修改 Checkpoint、不获取 Worker ownership；已完成事实及状态由调用方提供。
关键依赖：WorkflowDagResumePlanner、WorkflowDagBranchStateMergeService；真正 Node 执行仍由 WorkflowRuntime / Worker 负责。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_state_merge import WorkflowDagBranchState, WorkflowDagBranchStateMergeService


@dataclass(frozen=True)
class WorkflowDagResumeRuntimePlan:
    """DAG Resume Runtime 的确定性多 Node frontier 执行计划。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_ids: tuple[str, ...]
    nodes: tuple[dict, ...]
    state_data: dict
    selected_predecessor_node_ids: tuple[tuple[str, tuple[str, ...]], ...] = ()
    decision_fingerprint: str = ""

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
    def plan(*, definition: dict, completed_node_ids: set[str] | frozenset[str], state_data: dict | None = None,
             branch_state_data: Mapping[str, Mapping[str, object]] | None = None,
             state_data_by_node: Mapping[str, Mapping[str, object]] | None = None) -> WorkflowDagResumeRuntimePlan:
        """生成当前 Runtime 可以执行的 DAG Resume frontier 计划。

        Args:
            definition: 已冻结的 Workflow Version DAG Definition。
            completed_node_ids: 已验证的持久化完成事实集合。
            state_data: 已有单 frontier Resume 的兼容输入状态。
            branch_state_data: 多 frontier 每个分支独立状态，必须来自持久化事实。
            state_data_by_node: 已完成 Node 的持久化输出，用于 Conditional Branching 重新计算 frontier。

        Returns:
            Runtime 可消费的确定性 frontier、状态快照、有效 predecessor 与 decision fingerprint。

        Raises:
            ValueError: DAG、条件边、frontier、状态输入或 Planner fingerprint 不满足 Contract。
        """
        if state_data is not None and not isinstance(state_data, dict):
            raise ValueError("DAG Resume Runtime state_data 必须为对象")
        if branch_state_data is not None and not isinstance(branch_state_data, Mapping):
            raise ValueError("DAG Resume Runtime branch_state_data 必须为对象")
        plan = WorkflowDagResumePlanner.plan(
            definition=definition,
            completed_node_ids=completed_node_ids,
            state_data_by_node=state_data_by_node,
        )
        if not plan.decision_fingerprint:
            raise ValueError("DAG Resume Planner 未生成 decision fingerprint")
        node_by_id = {node["id"]: node for node in definition["nodes"] if isinstance(node, dict) and isinstance(node.get("id"), str)}
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
            merge_plan = WorkflowDagBranchStateMergeService.merge(tuple(
                WorkflowDagBranchState(node_id=node_id, state_data=branch_state_data[node_id])
                for node_id in frontier_node_ids
            ))
            merged_state_data = merge_plan.state_data
        return WorkflowDagResumeRuntimePlan(
            completed_node_ids=plan.completed_node_ids,
            frontier_node_ids=frontier_node_ids,
            nodes=nodes,
            state_data=merged_state_data,
            selected_predecessor_node_ids=plan.selected_predecessor_node_ids,
            decision_fingerprint=plan.decision_fingerprint,
        )
