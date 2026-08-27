"""Workflow DAG Resume Contract 校验模块。

职责：冻结并校验 Workflow Definition 的图结构及 Conditional Branching Contract。
边界：只做纯内存结构、拓扑与条件结构校验，不读取数据库、不推断完成事实、不生成 frontier、不执行 Runtime。
关键依赖：WorkflowConditionEvaluator；输入为 Workflow Version Definition 的 nodes / edges。
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from app.services.workflow.checkpoint.recovery.condition import WorkflowConditionEvaluator


@dataclass(frozen=True)
class WorkflowDagEdge:
    """经过 Contract 校验的有向边及其可选条件。"""

    source: str
    target: str
    condition: dict[str, Any] | None = None
    default: bool = False


@dataclass(frozen=True)
class WorkflowDagContract:
    """经过 Contract 校验的 DAG 图快照。"""

    node_ids: tuple[str, ...]
    edges: tuple[WorkflowDagEdge, ...]
    roots: tuple[str, ...]


class WorkflowDagContractValidator:
    """校验 DAG Resume 与 Conditional Branching 允许使用的 Workflow Definition 图结构。"""

    @staticmethod
    def validate(*, definition: dict) -> WorkflowDagContract:
        """校验并冻结 DAG Definition 的结构、拓扑与条件边安全边界。

        Args:
            definition: Workflow Version 的完整 Definition，必须包含 nodes 与非空 edges。

        Returns:
            只包含稳定 Node ID、经过校验的 Edge 以及根节点的不可变 DAG Contract。

        Raises:
            ValueError: Definition、Node、Edge、条件表达式、重复边、孤立节点或拓扑结构不满足 Contract。
        """
        if not isinstance(definition, dict):
            raise ValueError("DAG Workflow definition 必须为对象")
        nodes = definition.get("nodes")
        edges = definition.get("edges")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("DAG Workflow 必须包含非空 nodes")
        if not isinstance(edges, list) or not edges:
            raise ValueError("DAG Workflow 必须包含非空 edges")

        node_ids: list[str] = []
        node_id_set: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("DAG Node 必须为对象")
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                raise ValueError("DAG Node id 必须为非空字符串")
            if node_id in node_id_set:
                raise ValueError(f"DAG Node id 重复: {node_id}")
            node_id_set.add(node_id)
            node_ids.append(node_id)

        parsed_edges: list[WorkflowDagEdge] = []
        edge_set: set[tuple[str, str]] = set()
        outgoing: dict[str, list[str]] = defaultdict(list)
        incoming_count: dict[str, int] = {node_id: 0 for node_id in node_ids}
        source_modes: dict[str, str] = {}
        default_sources: set[str] = set()

        for edge in edges:
            if not isinstance(edge, dict):
                raise ValueError("DAG Edge 必须为对象")
            if set(edge) - {"source", "target", "condition", "default"}:
                raise ValueError("DAG Edge 包含未允许字段")
            if "condition" in edge and "default" in edge:
                raise ValueError("DAG Edge condition 与 default 不能同时存在")
            source = edge.get("source")
            target = edge.get("target")
            if not isinstance(source, str) or not source or not isinstance(target, str) or not target:
                raise ValueError("DAG Edge source / target 必须为非空字符串")
            if source not in node_id_set or target not in node_id_set:
                raise ValueError("DAG Edge 必须引用已存在的 Node")
            if source == target:
                raise ValueError("DAG Edge 不允许 self-loop")
            key = (source, target)
            if key in edge_set:
                raise ValueError(f"DAG Edge 重复: {source} -> {target}")
            edge_set.add(key)

            has_condition = "condition" in edge
            is_default = edge.get("default", False) is True
            if "default" in edge and edge.get("default") is not True:
                raise ValueError("DAG Edge default 只能为 true")
            mode = "conditional" if has_condition or is_default else "unconditional"
            previous_mode = source_modes.get(source)
            if previous_mode is not None and previous_mode != mode:
                raise ValueError("同一 source 不允许混用无条件边与 condition/default 边")
            source_modes[source] = mode
            if is_default:
                if source in default_sources:
                    raise ValueError(f"同一 source 最多一个 default edge: {source}")
                default_sources.add(source)
            condition = edge.get("condition")
            if has_condition:
                if not isinstance(condition, dict):
                    raise ValueError("DAG Edge condition 必须为对象")
                WorkflowConditionEvaluator.validate(condition)
            parsed_edges.append(WorkflowDagEdge(source=source, target=target, condition=condition, default=is_default))
            outgoing[source].append(target)
            incoming_count[target] += 1

        isolated = [node_id for node_id in node_ids if not outgoing[node_id] and incoming_count[node_id] == 0]
        if isolated:
            raise ValueError(f"DAG 不允许孤立 Node: {isolated[0]}")
        roots = tuple(node_id for node_id in node_ids if incoming_count[node_id] == 0)
        if len(roots) != 1:
            raise ValueError("DAG Workflow 第一版 Resume 必须只有一个 root")

        queue = deque(roots)
        visited_count = 0
        remaining_incoming = dict(incoming_count)
        while queue:
            source = queue.popleft()
            visited_count += 1
            for target in outgoing[source]:
                remaining_incoming[target] -= 1
                if remaining_incoming[target] == 0:
                    queue.append(target)
        if visited_count != len(node_ids):
            raise ValueError("DAG Workflow 不允许存在循环")

        return WorkflowDagContract(node_ids=tuple(node_ids), edges=tuple(parsed_edges), roots=roots)
