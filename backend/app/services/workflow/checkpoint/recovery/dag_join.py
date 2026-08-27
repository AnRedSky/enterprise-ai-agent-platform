"""Workflow DAG Join Readiness 领域模块。

职责：判断 DAG Join Node 是否已经具备安全执行条件，并构造有效 predecessor 的状态输入。
边界：只消费调用方已经计算并验证的 completed Node 与有效 predecessor，不读取数据库、不执行条件表达式、不修改 Execution。
关键依赖：WorkflowDagBranchStateMergeService；Conditional predecessor 必须由统一 DAG Planner 提供。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from app.services.workflow.checkpoint.recovery.dag_state_merge import WorkflowDagBranchState, WorkflowDagBranchStateMergeService


@dataclass(frozen=True)
class WorkflowDagJoinReadiness:
    """Join Node 的确定性 readiness 事实。"""

    node_id: str
    predecessor_node_ids: tuple[str, ...]
    ready: bool
    state_data: dict[str, object] | None


class WorkflowDagJoinReadinessService:
    """基于有效 predecessor 完成事实安全计算 Join readiness。"""

    @staticmethod
    def evaluate(*, definition: dict, node_id: str, completed_node_ids: set[str] | frozenset[str],
                 node_outputs: Mapping[str, Mapping[str, object]], predecessor_node_ids: tuple[str, ...] | None = None) -> WorkflowDagJoinReadiness:
        """计算 Join Node 是否可执行，并合并有效 predecessor 的状态输入。

        Args:
            definition: 已通过 DAG Contract 校验的 Workflow Definition。
            node_id: 当前待判断的 Node ID。
            completed_node_ids: 已从持久化 Node Execution 验证的 completed Node 集合。
            node_outputs: 已完成 Node 的持久化输出状态。
            predecessor_node_ids: 可选的有效 predecessor 快照；由 Conditional Planner 提供，省略时使用 Definition 入边。

        Returns:
            包含有效 predecessor 列表、ready 标记和安全合并状态的 readiness 事实。

        Raises:
            ValueError: Node、完成事实、predecessor 输出或状态合并不满足 Contract。
        """
        nodes = definition.get("nodes")
        if not isinstance(nodes, list):
            raise ValueError("DAG Join Definition 必须包含 nodes 数组")
        node_ids = {node.get("id") for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}
        if node_id not in node_ids:
            raise ValueError(f"DAG Join Node 不存在: {node_id}")
        if not isinstance(completed_node_ids, (set, frozenset)):
            raise ValueError("DAG Join completed_node_ids 必须为 set 或 frozenset")
        if not isinstance(node_outputs, Mapping):
            raise ValueError("DAG Join node_outputs 必须为对象")

        if predecessor_node_ids is None:
            predecessors = sorted(
                edge.get("source") for edge in definition.get("edges", []) or []
                if isinstance(edge, dict) and edge.get("target") == node_id
            )
            predecessor_node_ids = tuple(item for item in predecessors if isinstance(item, str))
        else:
            predecessor_node_ids = tuple(predecessor_node_ids)
        if not predecessor_node_ids:
            raise ValueError(f"DAG Join Node {node_id} 必须至少存在一个 predecessor")

        missing_completed = [item for item in predecessor_node_ids if item not in completed_node_ids]
        if missing_completed:
            return WorkflowDagJoinReadiness(node_id=node_id, predecessor_node_ids=predecessor_node_ids, ready=False, state_data=None)

        branches: list[WorkflowDagBranchState] = []
        for predecessor_id in predecessor_node_ids:
            if predecessor_id not in node_outputs:
                raise ValueError(f"DAG Join Node {node_id} 缺少 predecessor output: {predecessor_id}")
            output = node_outputs[predecessor_id]
            if not isinstance(output, Mapping):
                raise ValueError(f"DAG Join predecessor output 必须为对象: {predecessor_id}")
            branches.append(WorkflowDagBranchState(node_id=predecessor_id, state_data=deepcopy(dict(output))))
        merge_plan = WorkflowDagBranchStateMergeService.merge(tuple(branches))
        return WorkflowDagJoinReadiness(node_id=node_id, predecessor_node_ids=predecessor_node_ids, ready=True, state_data=deepcopy(merge_plan.state_data))
