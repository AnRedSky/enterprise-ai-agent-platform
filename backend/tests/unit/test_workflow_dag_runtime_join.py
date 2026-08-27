"""Workflow Runtime Join 与 Recovery Trace Continuity 单元测试。

职责：验证 Join frontier 使用持久化 predecessor state，并验证 Recovery trace_id 能从持久化 lineage 延续到 Runtime。
边界：不连接 PostgreSQL、不启动 Worker、不调用真实 Provider。
关键依赖：WorkflowRuntime、WorkflowRecoveryTraceLinkService、WorkflowRecoveryTelemetry。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.runtime.workflow import WorkflowRuntime
from app.runtime.workflow.runtime import WorkflowRuntime as BaseWorkflowRuntime


@pytest.fixture
def join_definition():
    return {
        "nodes": [
            {"id": "root", "type": "input"},
            {"id": "left", "type": "input"},
            {"id": "right", "type": "input"},
            {"id": "join", "type": "join"},
            {"id": "output", "type": "output"},
        ],
        "edges": [
            {"source": "root", "target": "left"},
            {"source": "root", "target": "right"},
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
            {"source": "join", "target": "output"},
        ],
    }


def test_runtime_accepts_join_node(join_definition):
    nodes = WorkflowRuntime.validate_definition(join_definition)
    assert [node["type"] for node in nodes] == ["input", "input", "input", "join", "output"]


@pytest.mark.asyncio
async def test_join_node_is_pure_state_aggregation():
    runtime = WorkflowRuntime(AsyncMock())
    state = {"left": 1, "right": 2}
    result = await runtime.execute_node(
        {"id": "join", "type": "join", "config": {}},
        state,
        uuid4(),
        False,
        uuid4(),
    )
    assert result == state
    assert result is not state


@pytest.mark.asyncio
async def test_resume_context_uses_persisted_predecessor_outputs_for_join(join_definition):
    db = AsyncMock()
    root = SimpleNamespace(node_id="root", output_data={"root": 1})
    left = SimpleNamespace(node_id="left", output_data={"left": 2})
    right = SimpleNamespace(node_id="right", output_data={"right": 3})
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [root, left, right])))
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(id=uuid4(), resume_of_execution_id=uuid4())

    plan, branch_state_data = await runtime._resolve_resume_context(execution, join_definition, {"stale": True})

    assert plan.frontier_node_ids == ("join",)
    assert plan.state_data == {"left": 2, "right": 3}
    assert branch_state_data == {"join": {"left": 2, "right": 3}}


@pytest.mark.asyncio
async def test_join_runtime_does_not_use_stale_resume_input(join_definition):
    db = AsyncMock()
    left = SimpleNamespace(node_id="left", output_data={"left": 10})
    right = SimpleNamespace(node_id="right", output_data={"right": 20})
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [left, right])))
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(id=uuid4(), resume_of_execution_id=uuid4())

    plan, _ = await runtime._resolve_resume_context(execution, join_definition, {"left": -1, "right": -1})

    assert plan.state_data == {"left": 10, "right": 20}


@pytest.mark.asyncio
async def test_runtime_continues_persisted_recovery_trace_to_base_runtime(monkeypatch, caplog):
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    version = SimpleNamespace()
    actor_id = uuid4()
    db = AsyncMock()

    class _TraceLink:
        def __init__(self, _db):
            pass

        async def get_trace_id(self, _execution):
            return "trace-recovery-123"

    monkeypatch.setattr("app.runtime.workflow.dag_runtime.WorkflowRecoveryTraceLinkService", _TraceLink)
    monkeypatch.setattr(BaseWorkflowRuntime, "execute", AsyncMock(return_value={"ok": True}))
    caplog.set_level("INFO")

    runtime = WorkflowRuntime(db)
    result = await runtime.execute(execution, version, actor_id)

    assert result == {"ok": True}
    events = [record for record in caplog.records if record.trace_id == "trace-recovery-123"]
    assert [record.message for record in events] == [
        "workflow.recovery.runtime.started",
        "workflow.recovery.runtime.finished",
    ]
    assert events[-1].outcome == "completed"
