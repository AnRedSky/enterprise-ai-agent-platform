from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow_runtime import WorkflowRuntime


def test_workflow_runtime_accepts_only_supported_sequential_nodes():
    nodes = WorkflowRuntime.validate_definition({
        "nodes": [
            {"id": "input", "type": "input"},
            {"id": "agent", "type": "agent", "config": {"agent_id": str(uuid4())}},
            {"id": "output", "type": "output"},
        ]
    })
    assert [node["type"] for node in nodes] == ["input", "agent", "output"]


@pytest.mark.parametrize("definition", [{}, {"nodes": []}, {"nodes": [{"id": "a", "type": "unknown"}]}])
def test_workflow_runtime_rejects_invalid_definition(definition):
    with pytest.raises(HTTPException) as exc:
        WorkflowRuntime.validate_definition(definition)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_input_and_output_nodes_preserve_payload():
    runtime = WorkflowRuntime(AsyncMock())
    actor = uuid4()
    session = uuid4()
    payload = {"input": "hello", "value": 1}
    assert await runtime.execute_node({"id": "i", "type": "input", "config": {}}, payload, actor, False, session) == payload
    assert await runtime.execute_node({"id": "o", "type": "output", "config": {}}, payload, actor, False, session) == payload


@pytest.mark.asyncio
async def test_agent_node_uses_published_agent_version_and_gateway():
    db = AsyncMock()
    agent_id = uuid4()
    owner_id = uuid4()
    version_id = uuid4()
    agent = SimpleNamespace(id=agent_id, owner_id=owner_id, status="published", published_version_id=version_id)
    version = SimpleNamespace(id=version_id, agent_id=agent_id, system_prompt="system", model_id="mock", version="1.0.0")
    first = SimpleNamespace(scalar_one_or_none=lambda: agent)
    second = SimpleNamespace(scalar_one_or_none=lambda: version)
    db.execute = AsyncMock(side_effect=[first, second])
    runtime = WorkflowRuntime(db)
    runtime.gateway.generate = AsyncMock(return_value=SimpleNamespace(content="ok", usage=None))

    result = await runtime.execute_node(
        {"id": "agent", "type": "agent", "config": {"agent_id": str(agent_id)}},
        {"input": "hello"}, owner_id, False, uuid4(),
    )
    assert result["content"] == "ok"
    runtime.gateway.generate.assert_awaited_once()
