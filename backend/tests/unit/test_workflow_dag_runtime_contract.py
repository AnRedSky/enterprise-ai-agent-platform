"""Workflow DAG Runtime Contract 回归测试。

职责：验证普通顺序 Workflow 的空 edges 不会误进入 DAG Contract 校验，同时保证真正存在 edges 时仍执行 DAG 校验。
边界：只覆盖 Runtime Definition 的纯内存 Contract 行为，不连接数据库或启动服务。
关键依赖：app.runtime.workflow.WorkflowRuntime、pytest。
"""

import pytest
from fastapi import HTTPException

from app.runtime.workflow import WorkflowRuntime


def _definition(*, edges):
    return {
        "nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ],
        "edges": edges,
        "config": {},
    }


def test_empty_edges_are_treated_as_sequential_workflow():
    """验证 edges: [] 与未配置 edges 一样走顺序 Runtime，不应被误判为 DAG。"""
    nodes = WorkflowRuntime.validate_definition(_definition(edges=[]))

    assert [node["id"] for node in nodes] == ["input", "output"]


def test_non_empty_edges_still_require_valid_dag_contract():
    """验证真正启用 DAG 时仍必须经过 DAG Contract 校验。"""
    with pytest.raises(HTTPException, match="DAG Edge"):
        WorkflowRuntime.validate_definition(
            _definition(edges=[{"source": "input", "target": "missing"}])
        )
