from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.runtime.workflow import WorkflowRuntime


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
