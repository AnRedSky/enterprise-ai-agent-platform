from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.runtime.workflow.dag_runtime import WorkflowRuntime


@pytest.mark.asyncio
async def test_initial_multi_root_dag_creates_independent_branch_states_from_input():
    """验证首次执行存在多个 root 时，每个 frontier 都获得独立输入快照。"""
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [])
    )
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(
        id=uuid4(),
        resume_of_execution_id=None,
    )
    definition = {
        "nodes": [
            {"id": "left", "type": "input", "config": {}},
            {"id": "right", "type": "input", "config": {}},
            {"id": "join", "type": "join", "config": {}},
        ],
        "edges": [
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
        ],
    }
    input_data = {"request_id": "r-1", "content": "hello"}

    plan, branch_state_data = await runtime._resolve_dag_context(
        execution,
        definition,
        input_data,
    )

    assert plan.frontier_node_ids == ("left", "right")
    assert branch_state_data == {
        "left": input_data,
        "right": input_data,
    }
    assert plan.selected_predecessor_node_ids == ()


def test_dag_runtime_join_node_is_registered_without_reimplementing_base_runtime():
    """验证 Join 只扩展 Node 类型，不复制基础 Runtime 的执行能力。"""
    assert "join" in WorkflowRuntime.NODE_TYPES
    assert "agent" in WorkflowRuntime.NODE_TYPES
    assert WorkflowRuntime.execute_node.__qualname__.startswith("WorkflowRuntime.execute_node")
