"""Workflow DAG Resume Frontier 规划模块。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from app.services.workflow.checkpoint.recovery.condition import WorkflowConditionEvaluator
from app.services.workflow.checkpoint.recovery.dag_contract import WorkflowDagContractValidator


@dataclass(frozen=True)
class WorkflowDagResumePlan:
    """DAG Resume 的确定性 frontier 计划及有效 predecessor 快照。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_ids: tuple[str, ...]
    selected_predecessor_node_ids: tuple[tuple[str, tuple[str, ...]], ...] = ()
    decision_fingerprint: str = ""


class WorkflowDagResumePlanner:
    """根据已完成 Node 及其持久化 state 计算下一批可恢复 frontier。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        completed_node_ids: set[str] | frozenset[str],
        state_data_by_node: Mapping[str, Mapping[str, object]] | None = None,
    ) -> WorkflowDagResumePlan:
        """计算 DAG Resume frontier，并在有条件边时确定性选择后继。"""
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
        ordered_completed = tuple(node_id for node_id in contract.node_ids if node_id in completed_node_ids)
        decision_input = {
            "workflow_node_ids": list(contract.node_ids),
            "completed_node_ids": list(ordered_completed),
            "frontier_node_ids": list(frontier),
            "selected_predecessors": [
                {"node_id": node_id, "predecessor_node_ids": list(predecessors)}
                for node_id, predecessors in selected
            ],
            "condition_state": {
                node_id: state_data_by_node[node_id]
                for node_id in sorted(state_data_by_node)
                if node_id in completed_node_ids and any(
                    edge.condition is not None or edge.default for edge in outgoing[node_id]
                )
            },
        }
        try:
            canonical = json.dumps(
                decision_input,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"DAG Resume 无法生成确定性 decision fingerprint：condition state 必须是 JSON-safe 数据: {exc}"
            ) from exc
        decision_fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
        return WorkflowDagResumePlan(
            completed_node_ids=ordered_completed,
            frontier_node_ids=frontier,
            selected_predecessor_node_ids=selected,
            decision_fingerprint=decision_fingerprint,
        )
