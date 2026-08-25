"""验证 Workflow 执行重试过程中节点状态转换保持既有运行时语义。

测试范围：验证 WorkflowExecutionService 在节点执行失败并进入重试时，
通过 canonical WorkflowRuntime 执行入口，并按 running → failed → running → failed 顺序推进状态。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow import WorkflowRuntime
from app.services.workflow import WorkflowExecutionService


@pytest.mark.asyncio
async def test_retry_attempt_returns_node_to_running_before_next_runtime_call(monkeypatch):
    service = WorkflowExecutionService(AsyncMock())
    service.governance.audit = AsyncMock(); service.governance.trace = AsyncMock()
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), created_by=uuid4(), status="pending",
                                input_data={"input": "retry-transition"}, started_at=None, ended_at=None,
                                current_node_id=None, output_data=None, error_code=None, error_message=None,
                                worker_owner=None)
    version = SimpleNamespace(definition={"config": {"timeout_ms": 1000, "retry_budget": {"max_retries": 2}}, "nodes": [{
        "id": "unstable", "type": "input", "config": {"timeout_ms": 1000, "retry": {"max_attempts": 2,
        "backoff_ms": 0, "max_backoff_ms": 0, "jitter_ms": 0, "retryable_error_codes": ["HTTP_503"]}}}]})

    async def transition(execution, target_status, **kwargs):
        execution.status = target_status
        if kwargs.get("error_code"): execution.error_code = kwargs["error_code"]
        return execution

    calls: list[str] = []
    async def transition_node(_execution, _node_id, target_status, **_kwargs):
        calls.append(target_status)
        attempt = 1 if calls.count("failed") == 1 else 2
        return SimpleNamespace(attempt=attempt)

    service.transition = AsyncMock(side_effect=transition)
    service.transition_node = AsyncMock(side_effect=transition_node)

    async def fail_execute(*_args, **_kwargs):
        raise HTTPException(503, "upstream unavailable")

    monkeypatch.setattr(WorkflowRuntime, "execute_node", fail_execute)
    with pytest.raises(HTTPException) as exc:
        await service.run(execution, version, uuid4())
    assert exc.value.status_code == 503
    assert calls == ["running", "failed", "running", "failed"]
