from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

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
        id=uuid4(), workflow_id=uuid4(), version="1", status="published", created_by=uuid4(),
        definition={"nodes": [{"id": "node-1", "type": "input", "config": {}}, {"id": "node-2", "type": "agent", "config": {}}]},
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


@pytest.mark.asyncio
async def test_persisted_node_attempt_limits_resume_retry_budget():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    persisted = SimpleNamespace(node_id="node-1", status="failed", attempt=2)
    result = MagicMock()
    result.scalar_one_or_none.return_value = persisted
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    runtime = DurableResumeWorkflowRuntime(db)
    service = MagicMock()
    node = {"id": "node-1", "type": "agent", "config": {"retry": {"max_attempts": 3}}}
    parent = AsyncMock()
    with patch.object(DurableResumeWorkflowRuntime.__mro__[1], "_execute_node_with_policy", new=parent):
        await runtime._execute_node_with_policy(service, execution, node, {"input": "x"}, uuid4(), False, 30000, 0, 0.0, [0])
    resumed_node = parent.await_args.args[2]
    assert resumed_node["config"]["retry"]["max_attempts"] == 1


@pytest.mark.asyncio
async def test_persisted_node_attempt_exhaustion_does_not_replay_node():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    persisted = SimpleNamespace(node_id="node-1", status="failed", attempt=3)
    result = MagicMock()
    result.scalar_one_or_none.return_value = persisted
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    runtime = DurableResumeWorkflowRuntime(db)
    node = {"id": "node-1", "type": "agent", "config": {"retry": {"max_attempts": 3}}}
    with pytest.raises(HTTPException, match="Retry 次数已耗尽"):
        await runtime._execute_node_with_policy(MagicMock(), execution, node, {"input": "x"}, uuid4(), False, 30000, 0, 0.0, [0])


@pytest.mark.asyncio
async def test_persisted_workflow_retry_budget_is_reduced_on_resume():
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    node = SimpleNamespace(attempt=2)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [node]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    runtime = DurableResumeWorkflowRuntime(db)
    parent = AsyncMock(return_value={"content": "done"})
    version = SimpleNamespace(
        id=uuid4(), workflow_id=uuid4(), version="1", status="published", created_by=uuid4(),
        definition={"nodes": [], "config": {"retry_budget": {"max_retries": 3}}},
    )
    with patch.object(DurableResumeWorkflowRuntime.__mro__[1], "execute", new=parent):
        await runtime.execute(execution, version, uuid4())
    resumed_version = parent.await_args.args[1]
    assert resumed_version.definition["config"]["retry_budget"]["max_retries"] == 2
