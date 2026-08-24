from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow import WorkflowRuntime
from app.services.workflow import WorkflowExecutionService


@pytest.mark.asyncio
async def test_retry_budget_exhaustion_fails_execution_and_records_governance(monkeypatch):
    service = WorkflowExecutionService(AsyncMock()); service.governance.audit = AsyncMock(); service.governance.trace = AsyncMock()
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), created_by=uuid4(), status="pending", input_data={"input": "retry"}, started_at=None, ended_at=None, current_node_id=None, output_data=None, error_code=None, error_message=None)
    version = SimpleNamespace(definition={"config": {"timeout_ms": 1000, "retry_budget": {"max_retries": 1}}, "nodes": [{"id": "unstable", "type": "input", "config": {"timeout_ms": 1000, "retry": {"max_attempts": 5, "backoff_ms": 0, "max_backoff_ms": 0, "jitter_ms": 0, "retryable_error_codes": ["HTTP_503"]}}}]})
    async def transition(execution, target_status, **kwargs):
        execution.status = target_status
        if kwargs.get("error_code"): execution.error_code = kwargs["error_code"]
        return execution
    node_calls = 0
    async def transition_node(execution, node_id, target_status, **kwargs):
        nonlocal node_calls
        node_calls += 1
        return SimpleNamespace(attempt=1 if node_calls <= 2 else 2)
    service.transition = AsyncMock(side_effect=transition); service.transition_node = AsyncMock(side_effect=transition_node)
    async def fail_execute(*_args, **_kwargs): raise HTTPException(503, "upstream unavailable")
    monkeypatch.setattr(WorkflowRuntime, "execute_node", fail_execute)
    with pytest.raises(HTTPException) as exc: await service.run(execution, version, uuid4())
    assert exc.value.status_code == 503; assert execution.status == "failed"; assert execution.error_code == "HTTP_503"
    assert any(call.args[2] == "node.retry.exhausted" and (call.kwargs.get("data") or {}).get("reason") == "retry_budget" for call in service.governance.trace.await_args_list)
    assert any(call.args[2] == "workflow.node.retry_exhausted" for call in service.governance.audit.await_args_list)


@pytest.mark.asyncio
async def test_retry_deadline_exhaustion_marks_workflow_timeout(monkeypatch):
    service = WorkflowExecutionService(AsyncMock()); service.governance.audit = AsyncMock(); service.governance.trace = AsyncMock()
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), created_by=uuid4(), status="pending", input_data={"input": "deadline"}, started_at=None, ended_at=None, current_node_id=None, output_data=None, error_code=None, error_message=None)
    version = SimpleNamespace(definition={"config": {"timeout_ms": 10, "retry_budget": {"max_retries": 5}}, "nodes": [{"id": "unstable", "type": "input", "config": {"timeout_ms": 1000, "retry": {"max_attempts": 3, "backoff_ms": 100, "max_backoff_ms": 100, "jitter_ms": 0, "retryable_error_codes": ["HTTP_503"]}}}]})
    async def transition(execution, target_status, **kwargs):
        execution.status = target_status
        if kwargs.get("error_code"): execution.error_code = kwargs["error_code"]
        return execution
    service.transition = AsyncMock(side_effect=transition); service.transition_node = AsyncMock(return_value=SimpleNamespace(attempt=1))
    async def fail_execute(*_args, **_kwargs): raise HTTPException(503, "upstream unavailable")
    monkeypatch.setattr(WorkflowRuntime, "execute_node", fail_execute)
    with pytest.raises(HTTPException) as exc: await service.run(execution, version, uuid4())
    assert exc.value.status_code == 504; assert execution.status == "failed"; assert execution.error_code == "WORKFLOW_TIMEOUT"
    assert any(call.args[2] == "node.retry.exhausted" and (call.kwargs.get("data") or {}).get("reason") == "workflow_deadline" for call in service.governance.trace.await_args_list)
