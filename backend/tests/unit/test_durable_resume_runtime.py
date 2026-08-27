from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow_worker.resume_runtime import DurableResumeWorkflowRuntime


@pytest.mark.asyncio
async def test_linear_resume_filters_completed_nodes():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    completed = SimpleNamespace(node_id="node-1")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [completed]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    version = SimpleNamespace(
        id=uuid4(),
        workflow_id=uuid4(),
        version="1",
        definition={
            "nodes": [
                {"id": "node-1", "type": "input", "config": {}},
                {"id": "node-2", "type": "agent", "config": {}},
            ],
        },
        status="published",
        created_by=uuid4(),
    )

    runtime = DurableResumeWorkflowRuntime(db)
    resumed = await runtime._resume_version(execution, version)

    assert [node["id"] for node in resumed.definition["nodes"]] == ["node-2"]


@pytest.mark.asyncio
async def test_dag_resume_keeps_definition_for_planner():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    db = MagicMock()
    runtime = DurableResumeWorkflowRuntime(db)
    version = SimpleNamespace(definition={"nodes": [], "edges": [{"source": "a", "target": "b"}]})

    resumed = await runtime._resume_version(execution, version)

    assert resumed is version
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_fresh_linear_execution_keeps_all_nodes():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    version = SimpleNamespace(definition={"nodes": [{"id": "node-1"}]})

    runtime = DurableResumeWorkflowRuntime(db)
    resumed = await runtime._resume_version(execution, version)

    assert resumed is version


@pytest.mark.asyncio
async def test_all_completed_linear_nodes_are_terminalized_without_replay():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), input_data={"input": "x"}, output_data=None)
    completed = SimpleNamespace(node_id="node-1", output_data={"content": "done"})
    result = MagicMock()
    result.scalars.return_value.all.return_value = [completed]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    service = MagicMock()
    service.transition = AsyncMock()
    runtime = DurableResumeWorkflowRuntime(db, execution_service=service)
    version = SimpleNamespace(definition={"nodes": [{"id": "node-1", "type": "agent", "config": {}}]})

    assert await runtime._complete_if_all_nodes_resumed(execution, version, uuid4()) is True
    service.transition.assert_awaited_once()
