import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow_execution import WorkflowExecutionService


def test_timeout_policy_defaults_and_bounds():
    assert WorkflowRuntime.resolve_timeout_ms({}) == WorkflowRuntime.DEFAULT_TIMEOUT_MS
    assert WorkflowRuntime.resolve_timeout_ms({"timeout_ms": 1500}) == 1500

    with pytest.raises(HTTPException) as exc:
        WorkflowRuntime.resolve_timeout_ms({"timeout_ms": 0})
    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        WorkflowRuntime.resolve_timeout_ms({"timeout_ms": WorkflowRuntime.MAX_TIMEOUT_MS + 1})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_run_marks_workflow_timeout_as_failed(monkeypatch):
    service = WorkflowExecutionService(AsyncMock())
    service.governance.audit = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), status="pending", input_data={"input": "slow"}
    )
    version = SimpleNamespace(
        definition={
            "config": {"timeout_ms": 10},
            "nodes": [{"id": "slow", "type": "input", "config": {"timeout_ms": 1}}],
        }
    )

    async def slow_execute(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return {"ok": True}

    monkeypatch.setattr(WorkflowRuntime, "execute_node", slow_execute)

    async def transition(execution, target_status, **kwargs):
        execution.status = target_status
        return execution

    service.transition = AsyncMock(side_effect=transition)
    service.transition_node = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await service.run(execution, version, uuid4())

    assert exc.value.status_code == 504
    failed_node_call = service.transition_node.await_args_list[-1]
    assert failed_node_call.args[2] == "failed"
    assert failed_node_call.kwargs["error_code"] == "NODE_TIMEOUT"
    failed_execution_call = [call for call in service.transition.await_args_list if call.args[1] == "failed"][-1]
    assert failed_execution_call.kwargs["error_code"] == "NODE_TIMEOUT"


@pytest.mark.asyncio
async def test_run_marks_workflow_deadline_timeout_as_failed(monkeypatch):
    service = WorkflowExecutionService(AsyncMock())
    service.governance.audit = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), status="pending", input_data={"input": "slow"}
    )
    version = SimpleNamespace(
        definition={
            "config": {"timeout_ms": 10},
            "nodes": [{"id": "slow", "type": "input", "config": {"timeout_ms": 30000}}],
        }
    )

    async def slow_execute(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return {"ok": True}

    monkeypatch.setattr(WorkflowRuntime, "execute_node", slow_execute)

    async def transition(execution, target_status, **kwargs):
        execution.status = target_status
        return execution

    service.transition = AsyncMock(side_effect=transition)
    service.transition_node = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await service.run(execution, version, uuid4())

    assert exc.value.status_code == 504
    failed_node_call = service.transition_node.await_args_list[-1]
    assert failed_node_call.args[2] == "failed"
    assert failed_node_call.kwargs["error_code"] == "WORKFLOW_TIMEOUT"
    failed_execution_call = [call for call in service.transition.await_args_list if call.args[1] == "failed"][-1]
    assert failed_execution_call.kwargs["error_code"] == "WORKFLOW_TIMEOUT"
