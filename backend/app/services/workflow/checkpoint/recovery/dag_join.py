"""Workflow DAG Join Readiness 领域模块。

职责：判断一个 DAG Join Node 是否已经具备安全执行条件，并构造其 predecessor 状态输入。
边界：只消费已经由调用方验证的 completed Node 事实与持久化输出，不读取数据库、不修改 Execution、不执行 Node。
关键依赖：Workflow DAG Definition、WorkflowNodeExecution 完成事实；真正的 Join Node 执行仍由 WorkflowRuntime 负责。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from app.services.workflow.checkpoint.recovery.dag_state_merge import (
    WorkflowDagBranchState,
    WorkflowDagBranchStateMergeService,
)


@dataclass(frozen=True)
class WorkflowDagJoinReadiness:
    """Join Node 的确定性 readiness 事实。"""

    node_id: str
    predecessor_node_ids: tuple[str, ...]
    ready: bool
    state_data: dict[str, object] | None


class WorkflowDagJoinReadinessService:
    """基于 predecessor 完成事实安全计算 Join readiness。"""

    @staticmethod
    def evaluate(
        *,
        definition: dict,
        node_id: str,
        completed_node_ids: set[str] | frozenset[str],
        node_outputs: Mapping[str, Mapping[str, object]],
    ) -> WorkflowDagJoinReadiness:
        """计算 Join Node 是否可执行，并合并全部 predecessor 的状态输入。

        Args:
            definition: 已通过 DAG Contract 校验的 Workflow Definition。
            node_id: 当前待判断的 Node ID。
            completed_node_ids: 已从持久化 Node Execution 验证的 completed Node 集合。
            node_outputs: 已完成 Node 的持久化输出状态；只允许提供对象状态。

        Returns:
            包含 predecessor 列表、ready 标记和安全合并状态的 readiness 事实。

        Raises:
            ValueError: Node 不存在、completed Node 非法、predecessor 输出缺失或状态存在冲突。

        设计意图：Join 的安全条件必须由“全部 predecessor 已完成”与“全部 predecessor 状态可安全合并”共同决定；
        不能因为 frontier Planner 已经发现 Node 就默认 Join 输入完整。状态冲突继续由统一 Merge Contract 拒绝，
        不允许 Join 层引入 last-write-wins。
        """
        nodes = definition.get("nodes")
        if not isinstance(nodes, list):
            raise ValueError("DAG Join Definition 必须包含 nodes 数组")
        node_ids = {
            node.get("id")
            for node in nodes
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        if node_id not in node_ids:
            raise ValueError(f"DAG Join Node 不存在: {node_id}")
        if not isinstance(completed_node_ids, (set, frozenset)):
            raise ValueError("DAG Join completed_node_ids 必须为 set 或 frozenset")
        if not isinstance(node_outputs, Mapping):
            raise ValueError("DAG Join node_outputs 必须为对象")

        predecessors = sorted(
            edge.get("source")
            for edge in definition.get("edges", []) or []
            if isinstance(edge, dict) and edge.get("target") == node_id
        )
        predecessor_node_ids = tuple(item for item in predecessors if isinstance(item, str))
        if not predecessor_node_ids:
            raise ValueError(f"DAG Join Node {node_id} 必须至少存在一个 predecessor")

        missing_completed = [item for item in predecessor_node_ids if item not in completed_node_ids]
        if missing_completed:
            return WorkflowDagJoinReadiness(
                node_id=node_id,
                predecessor_node_ids=predecessor_node_ids,
                ready=False,
                state_data=None,
            )

        branches: list[WorkflowDagBranchState] = []
        for predecessor_id in predecessor_node_ids:
            if predecessor_id not in node_outputs:
                raise ValueError(f"DAG Join Node {node_id} 缺少 predecessor output: {predecessor_id}")
            output = node_outputs[predecessor_id]
            if not isinstance(output, Mapping):
                raise ValueError(f"DAG Join predecessor output 必须为对象: {predecessor_id}")
            branches.append(
                WorkflowDagBranchState(
                    node_id=predecessor_id,
                    state_data=deepcopy(dict(output)),
                )
            )

        merge_plan = WorkflowDagBranchStateMergeService.merge(tuple(branches))
        return WorkflowDagJoinReadiness(
            node_id=node_id,
            predecessor_node_ids=predecessor_node_ids,
            ready=True,
            state_data=deepcopy(merge_plan.state_data),
        )
