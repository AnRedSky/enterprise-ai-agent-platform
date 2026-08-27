"""Workflow Runtime Durable Resume 单元测试模块。

职责：验证 WorkflowRuntime 如何依据持久化完成事实计算当前 DAG frontier。
边界：只测试 Runtime 的 Resume 规划与错误边界，不连接真实数据库、Worker 或 Provider。
关键依赖：WorkflowRuntime、DAG Resume Planner、DAG Resume Runtime Planner。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.workflow import WorkflowRuntime


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


def _execution(*, resume: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        resume_of_execution_id=uuid4() if resume else None,
        created_by=uuid4(),
        workflow_version_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_resume_runtime_selects_only_frontier_after_persisted_checkpoint(linear_definition: dict) -> None:
    db = _FakeDb([
        SimpleNamespace(node_id="prepare", status="completed", output_data={"input": "resume"}),
    ])
    runtime = WorkflowRuntime(db)
    plan, branch_state_data = await runtime._resolve_dag_context(
        _execution(),
        linear_definition,
        {"input": "resume"},
    )

    assert plan.frontier_node_ids == ("agent",)
    assert [node["id"] for node in plan.nodes] == ["agent"]
    assert branch_state_data == {"agent": {"input": "resume"}}
    assert db.calls == 1


@pytest.mark.asyncio
async def test_normal_execution_does_not_query_source_nodes(linear_definition: dict) -> None:
    db = _FakeDb([])
    runtime = WorkflowRuntime(db)

    result = await runtime._resolve_resume_context(
        _execution(resume=False),
        linear_definition,
        {"input": "normal"},
    )

    assert result is None
    assert db.calls == 0


@pytest.mark.asyncio
async def test_resume_runtime_supports_multiple_frontier_nodes(linear_definition: dict) -> None:
    linear_definition["edges"] = [
        {"source": "prepare", "target": "agent"},
        {"source": "prepare", "target": "finish"},
    ]
    db = _FakeDb([
        SimpleNamespace(node_id="prepare", status="completed", output_data={"input": "resume"}),
    ])
    runtime = WorkflowRuntime(db)

    plan, branch_state_data = await runtime._resolve_dag_context(
        _execution(),
        linear_definition,
        {"input": "resume"},
    )

    assert plan.frontier_node_ids == ("agent", "finish")
    assert [node["id"] for node in plan.nodes] == ["agent", "finish"]
    assert branch_state_data == {
        "agent": {"input": "resume"},
        "finish": {"input": "resume"},
    }


@pytest.mark.asyncio
async def test_resume_runtime_allows_no_frontier_after_all_nodes_completed(linear_definition: dict) -> None:
    db = _FakeDb([
        SimpleNamespace(node_id="prepare", status="completed", output_data={"input": "resume"}),
        SimpleNamespace(node_id="agent", status="completed", output_data={"content": "done"}),
        SimpleNamespace(node_id="finish", status="completed", output_data={"content": "done"}),
    ])
    runtime = WorkflowRuntime(db)

    plan, branch_state_data = await runtime._resolve_dag_context(
        _execution(),
        linear_definition,
        {"input": "resume"},
    )

    assert plan.frontier_node_ids == ()
    assert plan.nodes == ()
    assert branch_state_data == {}
