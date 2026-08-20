import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow_runtime import WorkflowRuntime
from app.services.workflow_execution import WorkflowExecutionService


def test_retry_policy_defaults_to_single_attempt():
    policy = WorkflowRuntime.resolve_retry_policy({})

    assert policy["max_attempts"] == 1
    assert "NODE_TIMEOUT" in policy["retryable_error_codes"]
    assert "HTTP_422" not in policy["retryable_error_codes"]


def test_retry_policy_rejects_unbounded_attempts_and_invalid_backoff():
    with pytest.raises(HTTPException):
        WorkflowRuntime.resolve_retry_policy({"retry": {"max_attempts": 6}})
    with pytest.raises(HTTPException):
        WorkflowRuntime.resolve_retry_policy({"retry": {"backoff_ms": -1}})
    with pytest.raises(HTTPException):
        WorkflowRuntime.resolve_retry_policy({"retry": {"max_backoff_ms": 100, "backoff_ms": 200}})


def test_retry_error_classification_only_marks_transient_errors_retryable_by_policy():
    policy = WorkflowRuntime.resolve_retry_policy({
        "retry": {"max_attempts": 3, "retryable_error_codes": ["HTTP_503", "NODE_TIMEOUT"]}
    })

    assert "HTTP_503" in policy["retryable_error_codes"]
    assert "HTTP_422" not in policy["retryable_error_codes"]
    assert WorkflowRuntime.classify_error(HTTPException(503, "upstream unavailable")) == "HTTP_503"
    assert WorkflowRuntime.classify_error(HTTPException(422, "invalid input")) == "HTTP_422"
    assert WorkflowRuntime.classify_error(asyncio.TimeoutError()) == "NODE_TIMEOUT"


def test_retry_delay_is_bounded_and_exponential():
    policy = WorkflowRuntime.resolve_retry_policy({
        "retry": {"max_attempts": 4, "backoff_ms": 100, "max_backoff_ms": 500, "jitter_ms": 50}
    })

    assert WorkflowRuntime.retry_delay_seconds(policy, 1, 0.0) == pytest.approx(0.1)
    assert WorkflowRuntime.retry_delay_seconds(policy, 2, 1.0) == pytest.approx(0.25)
    assert WorkflowRuntime.retry_delay_seconds(policy, 4, 1.0) == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_failed_node_can_resume_as_next_attempt():
    service = WorkflowExecutionService(SimpleNamespace())
    service.governance.trace = lambda *args, **kwargs: None

    async def trace(*args, **kwargs):
        return None

    service.governance.trace = trace
    service.db.execute = AsyncMockResult = None

    class FakeResult:
        def scalar_one_or_none(self):
            return node

    class FakeDB:
        def __init__(self):
            self.result = FakeResult()

        async def execute(self, _query):
            return self.result

        def add(self, _value):
            return None

        async def flush(self):
            return None

        async def commit(self):
            return None

        async def refresh(self, _value):
            return None

    node = SimpleNamespace(
        status="failed", attempt=1, started_at=None, ended_at=None,
        input_data=None, output_data=None, error_code="HTTP_503", error_message="temporary",
    )
    execution = SimpleNamespace(
        id=uuid4(), status="running", tenant_id=uuid4(), created_by=uuid4(), current_node_id=None,
    )
    service.db = FakeDB()
    service.governance.trace = trace

    result = await service.transition_node(execution, "agent", "running", input_data={"x": 1})

    assert result.attempt == 2
    assert result.status == "running"
    assert result.ended_at is None
    assert execution.current_node_id == "agent"
