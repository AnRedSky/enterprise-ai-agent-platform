"""Workflow Definition 历史兼容单元测试。

职责：锁定新 Definition Contract 与已发布历史空节点数据之间的兼容边界。
边界：只验证 Runtime 校验规则，不连接数据库、不模拟 Scheduler 执行。
"""

import pytest
from fastapi import HTTPException

from app.runtime.workflow import WorkflowRuntime


def test_new_definition_contract_rejects_empty_nodes() -> None:
    """新版本 Definition 默认必须包含至少一个合法节点。"""
    with pytest.raises(HTTPException, match="非空 nodes"):
        WorkflowRuntime.validate_definition({"nodes": []})


def test_historical_published_definition_allows_empty_nodes_when_explicitly_enabled() -> None:
    """只有受控的历史发布执行路径可以显式开启空节点兼容。"""
    assert WorkflowRuntime.validate_definition({"nodes": []}, allow_legacy_empty_nodes=True) == []


def test_legacy_compatibility_does_not_allow_invalid_node_items() -> None:
    """兼容边界只覆盖历史空节点，不得把非法节点数组放宽为可执行定义。"""
    with pytest.raises(HTTPException, match="Workflow node 必须为对象"):
        WorkflowRuntime.validate_definition({"nodes": ["legacy"]}, allow_legacy_empty_nodes=True)
