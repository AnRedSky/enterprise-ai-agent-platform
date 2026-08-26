"""Workflow DAG Resume Contract 单元测试。

职责：验证 DAG Definition 的结构、边引用、重复边、根节点、孤立节点与环路安全边界。
边界：只验证纯内存 Contract，不连接数据库、不读取 Node Execution、不调用 Runtime。
关键依赖：WorkflowDagContractValidator。
"""

from __future__ import annotations

import pytest

from app.services.workflow.checkpoint.recovery import WorkflowDagContractValidator


def _definition() -> dict:
    return {
        "nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "branch-a", "type": "agent", "config": {}},
            {"id": "branch-b", "type": "agent", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "branch-a"},
            {"source": "input", "target": "branch-b"},
            {"source": "branch-a", "target": "output"},
            {"source": "branch-b", "target": "output"},
        ],
    }


def test_dag_contract_freezes_nodes_edges_and_roots() -> None:
    contract = WorkflowDagContractValidator.validate(definition=_definition())

    assert contract.node_ids == ("input", "branch-a", "branch-b", "output")
    assert contract.roots == ("input",)
    assert [(edge.source, edge.target) for edge in contract.edges] == [
        ("input", "branch-a"),
        ("input", "branch-b"),
        ("branch-a", "output"),
        ("branch-b", "output"),
    ]


def test_dag_contract_rejects_multiple_roots() -> None:
    definition = _definition()
    definition["nodes"].append({"id": "second-input", "type": "input", "config": {}})
    definition["edges"].append({"source": "second-input", "target": "output"})

    with pytest.raises(ValueError, match="第一版 Resume 必须只有一个 root"):
        WorkflowDagContractValidator.validate(definition=definition)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda definition: definition["nodes"].append({"id": "branch-a", "type": "agent", "config": {}}), "DAG Node id 重复"),
        (lambda definition: definition["edges"].append({"source": "missing", "target": "output"}), "DAG Edge 必须引用已存在的 Node"),
        (lambda definition: definition["edges"].append({"source": "input", "target": "input"}), "DAG Edge 不允许 self-loop"),
        (lambda definition: definition["edges"].append({"source": "input", "target": "branch-a"}), "DAG Edge 重复"),
    ],
)
def test_dag_contract_rejects_invalid_graph(mutator, message: str) -> None:
    definition = _definition()
    mutator(definition)

    with pytest.raises(ValueError, match=message):
        WorkflowDagContractValidator.validate(definition=definition)


def test_dag_contract_rejects_extra_edge_fields() -> None:
    definition = _definition()
    definition["edges"][0]["condition"] = "x > 0"

    with pytest.raises(ValueError, match="DAG Edge 必须只包含 source / target 字段"):
        WorkflowDagContractValidator.validate(definition=definition)


def test_dag_contract_rejects_isolated_node() -> None:
    definition = _definition()
    definition["nodes"].append({"id": "isolated", "type": "agent", "config": {}})

    with pytest.raises(ValueError, match="DAG 不允许孤立 Node"):
        WorkflowDagContractValidator.validate(definition=definition)


def test_dag_contract_rejects_cycle() -> None:
    definition = _definition()
    definition["edges"] = [
        {"source": "input", "target": "branch-a"},
        {"source": "branch-a", "target": "branch-b"},
        {"source": "branch-b", "target": "branch-a"},
        {"source": "branch-b", "target": "output"},
    ]

    with pytest.raises(ValueError, match="DAG Workflow 不允许存在循环"):
        WorkflowDagContractValidator.validate(definition=definition)
