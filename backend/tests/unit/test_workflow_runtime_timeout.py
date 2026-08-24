import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow import WorkflowExecutionService


def test_timeout_policy_defaults_and_bounds():
    assert WorkflowRuntime.resolve_timeout_ms({}) == WorkflowRuntime.DEFAULT_TIMEOUT_MS
    assert WorkflowRuntime.resolve_timeout_ms({"timeout_ms": 1500}) == 1500
    with pytest.raises(HTTPException) as exc: WorkflowRuntime.resolve_timeout_ms({"timeout_ms": 0})
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc: WorkflowRuntime.resolve_timeout_ms({"timeout_ms": WorkflowRuntime.MAX_TIMEOUT_MS + 1})
    assert exc.value.status_code == 422


def _mock_execution():
    return SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), created_by=uuid4(), status="pending", input_data={"input": "slow"})


def _service():
    db = AsyncMock(); db.add = Mock()
    return WorkflowExecutionService(db)


@pytest.mark.asyncio
async def test_run_marks_workflow_timeout_as_failed(monkeypatch):
    service = _service(); service.governance.audit = AsyncMock(); execution = _mock_execution()
    version = SimpleNamespace(definition={"config": {"timeout_ms": 10}, "nodes": [{"id": "slow", "type": "input", "config": {"timeout_ms": 1}}]})
    async def slow_execute(*_args, **_kwargs): await asyncio.sleep(0.05); return {"ok": True}
    monkeypatch.setattr(WorkflowRuntime, "execute_node", slow_execute)
    async def transition(execution, target_status, **kwargs): execution.status = target_status; return execution
    service.transition = AsyncMock(side_effect=transition); service.transition_node = AsyncMock()
    with pytest.raises(HTTPException) as exc: await service.run(execution, version, uuid4())
    assert exc.value.status_code == 504
    failed_node_call = service.transition_node.await_args_list[-1]; assert failed_node_call.args[2] == "failed"; assert failed_node_call.kwargs["error_code"] == "NODE_TIMEOUT"
    failed_execution_call = [call for call in service.transition.await_args_list if call.args[1] == "failed"][-1]; assert failed_execution_call.kwargs["error_code"] == "NODE_TIMEOUT"


@pytest.mark.asyncio
async def test_run_marks_workflow_deadline_timeout_as_failed(monkeypatch):
    service = _service(); service.governance.audit = AsyncMock(); execution = _mock_execution()
    version = SimpleNamespace(definition={"config": {"timeout_ms": 10}, "nodes": [{"id": "slow", "type": "input", "config": {"timeout_ms": 30000}}]})
    async def slow_execute(*_args, **_kwargs): await asyncio.sleep(0.05); return {"ok": True}
    monkeypatch.setattr(WorkflowRuntime, "execute_node", slow_execute)
    async def transition(execution, target_status, **kwargs): execution.status = target_status; return execution
    service.transition = AsyncMock(side_effect=transition); service.transition_node = AsyncMock()
    with pytest.raises(HTTPException) as exc: await service.run(execution, version, uuid4())
    assert exc.value.status_code == 504
    failed_node_call = service.transition_node.await_args_list[-1]; assert failed_node_call.args[2] == "failed"; assert failed_node_call.kwargs["error_code"] == "WORKFLOW_TIMEOUT"
    failed_execution_call = [call for call in service.transition.await_args_list if call.args[1] == "failed"][-1]; assert failed_execution_call.kwargs["error_code"] == "WORKFLOW_TIMEOUT"


@pytest.mark.asyncio
async def test_run_exhausts_retry_budget_before_scheduling_retry(monkeypatch):
    service = _service(); service.governance.audit = AsyncMock(); service.governance.trace = AsyncMock(); execution = _mock_execution()
    version = SimpleNamespace(definition={"config": {"timeout_ms": 1000, "retry_budget": {"max_retries": 0}}, "nodes": [{"id": "transient", "type": "input", "config": {"timeout_ms": 1000, "retry": {"max_attempts": 3, "backoff_ms": 1, "jitter_ms": 0}}}]})
    async def fail_execute(*_args, **_kwargs): raise ConnectionError("temporary upstream failure")
    monkeypatch.setattr(WorkflowRuntime, "execute_node", fail_execute)
    async def transition(execution, target_status, **kwargs): execution.status = target_status; return execution
    service.transition = AsyncMock(side_effect=transition); service.transition_node = AsyncMock(return_value=SimpleNamespace(attempt=1))
    with pytest.raises(ConnectionError): await service.run(execution, version, uuid4())
    assert execution.status == "failed"; assert service.governance.audit.await_args_list[-1].args[2] == "workflow.node.retry_exhausted"; assert service.governance.trace.await_args_list[-1].args[2] == "node.retry.exhausted"; assert service.governance.trace.await_args_list[-1].kwargs["data"]["reason"] == "retry_budget"
    assert not any(call.args[2] == "running" for call in service.transition_node.await_args_list[1:])


@pytest.mark.asyncio
async def test_run_exhausts_retry_when_backoff_crosses_workflow_deadline(monkeypatch):
    service = _service(); service.governance.audit = AsyncMock(); service.governance.trace = AsyncMock(); execution = _mock_execution()
    version = SimpleNamespace(definition={"config": {"timeout_ms": 10, "retry_budget": {"max_retries": 3}}, "nodes": [{"id": "transient", "type": "input", "config": {"timeout_ms": 1000, "retry": {"max_attempts": 3, "backoff_ms": 100, "max_backoff_ms": 100, "jitter_ms": 0}}}]})
    async def fail_execute(*_args, **_kwargs): raise ConnectionError("temporary upstream failure")
    monkeypatch.setattr(WorkflowRuntime, "execute_node", fail_execute)
    async def transition(execution, target_status, **kwargs): execution.status = target_status; return execution
    service.transition = AsyncMock(side_effect=transition); service.transition_node = AsyncMock(return_value=SimpleNamespace(attempt=1))
    with pytest.raises(HTTPException) as exc: await service.run(execution, version, uuid4())
    assert exc.value.status_code == 504; assert execution.status == "failed"
    trace = service.governance.trace.await_args_list[-1]; assert trace.args[2] == "node.retry.exhausted"; assert trace.kwargs["error_code"] == "WORKFLOW_TIMEOUT"; assert trace.kwargs["data"]["reason"] == "workflow_deadline"
    assert not any(call.args[2] == "running" for call in service.transition_node.await_args_list[1:])
