"""Workflow DAG Resume Frontier 规划模块。

职责：根据已持久化完成 Node 集合、冻结 DAG Contract 与当前 Node state，计算下一批确定性 frontier 及有效 predecessor。
边界：只做纯内存计算，不读取数据库、不执行 Runtime、不获取 Worker ownership；条件判断统一由 Condition Evaluator 完成。
关键依赖：WorkflowDagContractValidator、WorkflowConditionEvaluator；完成事实及 Node 输出由调用方提供。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.services.workflow.checkpoint.recovery.condition import WorkflowConditionEvaluator
from app.services.workflow.checkpoint.recovery.dag_contract import WorkflowDagContractValidator


@dataclass(frozen=True)
class WorkflowDagResumePlan:
    """DAG Resume 的确定性 frontier 计划及有效 predecessor 快照。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_ids: tuple[str, ...]
    selected_predecessor_node_ids: tuple[tuple[str, tuple[str, ...]], ...] = ()


class WorkflowDagResumePlanner:
    """根据已完成 Node 及其持久化 state 计算下一批可恢复 frontier。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        completed_node_ids: set[str] | frozenset[str],
        state_data_by_node: Mapping[str, Mapping[str, object]] | None = None,
    ) -> WorkflowDagResumePlan:
        """计算 DAG Resume frontier，并在有条件边时确定性选择后继。

        Args:
            definition: 已冻结的 Workflow Version DAG Definition。
            completed_node_ids: 外部已经验证的持久化完成事实集合。
            state_data_by_node: 已完成 Node 的持久化输出状态；条件边从其 source 对应状态读取。

        Returns:
            按 Definition.nodes 顺序返回 completed、frontier 及每个 target 的有效 predecessor。

        Raises:
            ValueError: 完成事实、条件边状态或 DAG Contract 不满足约束。
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
        active_predecessors: dict[str, set[str]] = {node_id: set() for node_id in contract.node_ids}
        outgoing: dict[str, list] = {node_id: [] for node_id in contract.node_ids}
        for edge in contract.edges:
            predecessors[edge.target].add(edge.source)
            outgoing[edge.source].append(edge)

        has_conditional_edges = any(edge.condition is not None or edge.default for edge in contract.edges)
        if has_conditional_edges and completed_node_ids and state_data_by_node is None:
            raise ValueError("DAG Conditional Branching 必须提供 completed Node state_data")
        state_data_by_node = state_data_by_node or {}
        if not isinstance(state_data_by_node, Mapping):
            raise ValueError("DAG Resume state_data_by_node 必须为对象")
        unknown_state = set(state_data_by_node) - completed_node_ids
        if unknown_state:
            raise ValueError(f"DAG Resume state_data_by_node 存在未完成 Node: {sorted(unknown_state)[0]}")

        invalid_completed = sorted(
            node_id for node_id in completed_node_ids
            if not predecessors[node_id].issubset(completed_node_ids)
        )
        if invalid_completed:
            raise ValueError(f"DAG Resume completed Node 缺少已完成 predecessor: {invalid_completed[0]}")

        for source in contract.node_ids:
            if source not in completed_node_ids:
                continue
            edges = outgoing[source]
            if not edges:
                continue
            conditional = any(edge.condition is not None or edge.default for edge in edges)
            if not conditional:
                selected = edges
            else:
                source_state = state_data_by_node.get(source)
                if not isinstance(source_state, Mapping):
                    raise ValueError(f"DAG Conditional Branching 缺少 source state_data: {source}")
                matched = []
                default_edges = []
                for edge in edges:
                    if edge.default:
                        default_edges.append(edge)
                    elif edge.condition is not None and WorkflowConditionEvaluator.evaluate(edge.condition, source_state).matched:
                        matched.append(edge)
                selected = matched if matched else default_edges
            for edge in selected:
                active_predecessors[edge.target].add(source)

        frontier = tuple(
            node_id
            for node_id in contract.node_ids
            if node_id not in completed_node_ids
            and (
                not predecessors[node_id]
                or (not has_conditional_edges and predecessors[node_id].issubset(completed_node_ids))
                or (
                    has_conditional_edges
                    and active_predecessors[node_id]
                    and active_predecessors[node_id].issubset(completed_node_ids)
                )
            )
        )
        selected = tuple(
            (node_id, tuple(sorted(active_predecessors[node_id])))
            for node_id in contract.node_ids
            if active_predecessors[node_id]
        )
        return WorkflowDagResumePlan(
            completed_node_ids=tuple(node_id for node_id in contract.node_ids if node_id in completed_node_ids),
            frontier_node_ids=frontier,
            selected_predecessor_node_ids=selected,
        )
