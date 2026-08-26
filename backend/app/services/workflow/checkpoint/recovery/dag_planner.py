"""Workflow DAG Resume Frontier 规划模块。

职责：根据已持久化完成 Node 集合与冻结后的 DAG Contract，计算下一批可恢复 Node。
边界：只做纯内存计算，不读取数据库、不合并 state_data、不执行 Runtime、不获取 Worker ownership。
关键依赖：WorkflowDagContractValidator；完成事实必须由调用方从持久化 Node Execution / Checkpoint 提供。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.workflow.checkpoint.recovery.dag_contract import WorkflowDagContractValidator


@dataclass(frozen=True)
class WorkflowDagResumePlan:
    """DAG Resume 的确定性 frontier 计划。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_ids: tuple[str, ...]


class WorkflowDagResumePlanner:
    """根据已完成 Node 计算下一批所有 predecessor 均完成的 frontier。"""

    @staticmethod
    def plan(*, definition: dict, completed_node_ids: set[str] | frozenset[str]) -> WorkflowDagResumePlan:
        """计算 DAG Resume frontier。

        `completed_node_ids` 是外部已经验证的持久化完成事实；Planner 不推断它们，也不修改它们。
        frontier 按 Definition.nodes 的稳定顺序返回，避免数据库/集合迭代顺序造成非确定性。
        """
        contract = WorkflowDagContractValidator.validate(definition=definition)
        if not isinstance(completed_node_ids, (set, frozenset)):
            raise ValueError("DAG Resume completed_node_ids 必须为 set 或 frozenset")
        if not all(isinstance(node_id, str) and node_id for node_id in completed_node_ids):
            raise ValueError("DAG Resume completed_node_ids 必须只包含非空字符串")

        node_id_set = set(contract.node_ids)
        unknown_completed = completed_node_ids - node_id_set
        if unknown_completed:
            raise ValueError(f"DAG Resume 存在未知 completed Node: {sorted(unknown_completed)[0]}")

        predecessors: dict[str, set[str]] = {node_id: set() for node_id in contract.node_ids}
        for edge in contract.edges:
            predecessors[edge.target].add(edge.source)

        frontier = tuple(
            node_id
            for node_id in contract.node_ids
            if node_id not in completed_node_ids
            and predecessors[node_id].issubset(completed_node_ids)
        )
        return WorkflowDagResumePlan(
            completed_node_ids=tuple(node_id for node_id in contract.node_ids if node_id in completed_node_ids),
            frontier_node_ids=frontier,
        )
