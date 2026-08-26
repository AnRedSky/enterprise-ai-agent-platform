"""Workflow Runtime Durable Resume 单元测试模块。

职责：验证 WorkflowRuntime 如何依据 Source Execution 的持久化完成事实选择 Resume Node。
边界：只测试 Runtime 的 Resume 节点选择与错误边界，不连接真实数据库、Worker 或 Provider。
关键依赖：WorkflowRuntime、DAG Resume Runtime Planner。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow.runtime import WorkflowRuntime


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    async def execute(self, _query):
        self.calls += 1
        return _ScalarResult(self.rows)


@pytest.fixture
def linear_definition() -> dict:
    return {
        "config": {"timeout_ms": 5000, "retry_budget": {"max_retries": 0}},
        "nodes": [
            {"id": "prepare", "type": "input", "config": {}},
            {"id": "agent", "type": "agent", "config": {"agent_id": str(uuid4()), "prompt": "resume"}},
            {"id": "finish", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "prepare", "target": "agent"},
            {"source": "agent", "target": "finish"},
        ],
    }


@pytest.mark.asyncio
async def test_resume_runtime_selects_only_nodes_after_persisted_checkpoint(linear_definition: dict) -> None:
    db = _FakeDb([
        SimpleNamespace(node_id="prepare", status="completed"),
    ])
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(resume_of_execution_id=uuid4())

    nodes = await runtime._resolve_resume_nodes(
        execution,
        linear_definition,
        {"input": "resume"},
        WorkflowRuntime.validate_definition(linear_definition),
    )

    assert [node["id"] for node in nodes] == ["agent", "finish"]
    assert db.calls == 1


@pytest.mark.asyncio
async def test_normal_execution_does_not_query_source_nodes(linear_definition: dict) -> None:
    db = _FakeDb([])
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(resume_of_execution_id=None)
    fallback = WorkflowRuntime.validate_definition(linear_definition)

    nodes = await runtime._resolve_resume_nodes(execution, linear_definition, {"input": "normal"}, fallback)

    assert [node["id"] for node in nodes] == ["prepare", "agent", "finish"]
    assert db.calls == 0


@pytest.mark.asyncio
async def test_resume_runtime_rejects_multiple_frontier_nodes(linear_definition: dict) -> None:
    linear_definition["edges"] = [
        {"source": "prepare", "target": "agent"},
        {"source": "prepare", "target": "finish"},
    ]
    db = _FakeDb([
        SimpleNamespace(node_id="prepare", status="completed"),
    ])
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(resume_of_execution_id=uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await runtime._resolve_resume_nodes(
            execution,
            linear_definition,
            {"input": "resume"},
            WorkflowRuntime.validate_definition(linear_definition),
        )

    assert exc_info.value.status_code == 409
    assert "多个 frontier" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_resume_runtime_rejects_when_no_frontier_remains(linear_definition: dict) -> None:
    db = _FakeDb([
        SimpleNamespace(node_id="prepare", status="completed"),
        SimpleNamespace(node_id="agent", status="completed"),
        SimpleNamespace(node_id="finish", status="completed"),
    ])
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(resume_of_execution_id=uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await runtime._resolve_resume_nodes(
            execution,
            linear_definition,
            {"input": "resume"},
            WorkflowRuntime.validate_definition(linear_definition),
        )

    assert exc_info.value.status_code == 409
    assert "没有可继续执行" in str(exc_info.value.detail)
