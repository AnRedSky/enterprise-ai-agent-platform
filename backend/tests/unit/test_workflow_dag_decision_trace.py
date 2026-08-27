from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.runtime.workflow.dag_runtime import WorkflowRuntime


def _trace_result(trace_id=None):
    """构造同时覆盖 SQLAlchemy scalar 与 scalars 读取契约的测试结果。"""
    return SimpleNamespace(
        scalar_one_or_none=lambda: trace_id,
        scalars=lambda: SimpleNamespace(all=lambda: []),
    )


@pytest.mark.asyncio
async def test_dag_frontier_decision_is_persisted_without_business_state():
    db = AsyncMock()
    db.execute.side_effect = [
        _trace_result(),
        _trace_result(),
    ]
    governance = SimpleNamespace(trace=AsyncMock())
    execution_service = SimpleNamespace(governance=governance)
    runtime = WorkflowRuntime(db, execution_service=execution_service)
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        resume_of_execution_id=None,
    )
    definition = {
        "nodes": [
            {"id": "root", "type": "input", "config": {}},
            {"id": "left", "type": "input", "config": {}},
            {"id": "right", "type": "input", "config": {}},
            {"id": "join", "type": "join", "config": {}},
        ],
        "edges": [
            {"source": "root", "target": "left"},
            {"source": "root", "target": "right"},
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
        ],
    }

    await runtime._resolve_dag_context(execution, definition, {"input": "hello"})

    governance.trace.assert_awaited_once()
    call = governance.trace.await_args
    assert call.args[2] == "workflow.dag.frontier_decided"
    data = call.kwargs["data"]
    assert data["completed_node_ids"] == []
    assert data["frontier_node_ids"] == ["root"]
    assert data["selected_predecessors"] == []
    assert "input" not in data
    assert len(data["decision_id"]) == 64


@pytest.mark.asyncio
async def test_recovery_dag_decision_trace_contains_selected_predecessor_facts():
    db = AsyncMock()
    completed = SimpleNamespace(node_id="root", output_data={"status": "approved"})
    db.execute.side_effect = [
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [completed])),
        _trace_result(),
    ]
    governance = SimpleNamespace(trace=AsyncMock())
    execution_service = SimpleNamespace(governance=governance)
    runtime = WorkflowRuntime(db, execution_service=execution_service)
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        resume_of_execution_id=uuid4(),
    )
    definition = {
        "nodes": [
            {"id": "root", "type": "input", "config": {}},
            {"id": "approved", "type": "input", "config": {}},
            {"id": "rejected", "type": "input", "config": {}},
        ],
        "edges": [
            {"source": "root", "target": "approved", "condition": {"op": "eq", "path": "status", "value": "approved"}},
            {"source": "root", "target": "rejected", "default": True},
        ],
    }

    await runtime._resolve_dag_context(execution, definition, {"status": "approved"})

    governance.trace.assert_awaited_once()
    data = governance.trace.await_args.kwargs["data"]
    assert data["completed_node_ids"] == ["root"]
    assert data["frontier_node_ids"] == ["approved"]
    assert data["selected_predecessors"] == [{"node_id": "approved", "predecessor_node_ids": ["root"]}]
    assert "status" not in data
