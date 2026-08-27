from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.frontier_retry import FrontierRetryPolicy


def test_retry_policy_uses_bounded_exponential_backoff() -> None:
    policy = FrontierRetryPolicy(max_attempts=4, base_delay_seconds=2, max_delay_seconds=5)

    assert policy.can_retry(1)
    assert policy.delay_seconds(1) == 2
    assert policy.delay_seconds(2) == 4
    assert policy.delay_seconds(3) == 5
    assert not policy.can_retry(4)


def test_retry_policy_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        FrontierRetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        FrontierRetryPolicy(base_delay_seconds=-1)
    with pytest.raises(ValueError):
        FrontierRetryPolicy(base_delay_seconds=5, max_delay_seconds=4)


def test_retry_delay_rejects_invalid_attempt() -> None:
    with pytest.raises(ValueError):
        FrontierRetryPolicy().delay_seconds(0)


@pytest.mark.asyncio
async def test_schedule_frontier_retry_reuses_same_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.workflow import frontier_retry

    frontier_id = uuid4()
    now = datetime(2026, 8, 27, 10, 0, 0)
    frontier = SimpleNamespace(id=frontier_id, error_code=None, error_message=None, available_at=now)
    calls: list[dict] = []

    async def fake_transition(*args, **kwargs):
        calls.append(kwargs)
        return frontier

    monkeypatch.setattr(frontier_retry, "transition_owned_frontier", fake_transition)

    result = await frontier_retry.schedule_frontier_retry(
        object(),
        frontier=frontier,
        worker_owner="worker-a",
        attempt=2,
        now=now,
        error_code="NODE_TIMEOUT",
        error_message="node timed out",
        policy=FrontierRetryPolicy(max_attempts=4, base_delay_seconds=10),
    )

    assert result is frontier
    assert result.available_at == now + timedelta(seconds=20)
    assert result.error_code == "NODE_TIMEOUT"
    assert result.error_message == "node timed out"
    assert calls[0]["frontier_id"] == frontier_id
    assert calls[0]["target_status"] == "retry_wait"
    assert calls[0]["attempt"] == 2


@pytest.mark.asyncio
async def test_exhausted_retry_transitions_to_failed_and_preserves_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.workflow import frontier_retry

    frontier = SimpleNamespace(id=uuid4(), error_code=None, error_message=None)
    calls: list[dict] = []

    async def fake_transition(*args, **kwargs):
        calls.append(kwargs)
        return frontier

    monkeypatch.setattr(frontier_retry, "transition_owned_frontier", fake_transition)

    await frontier_retry.schedule_frontier_retry(
        object(),
        frontier=frontier,
        worker_owner="worker-a",
        attempt=3,
        now=datetime(2026, 8, 27, 10, 0, 0),
        error_code="NODE_TIMEOUT",
        error_message="node timed out",
        policy=FrontierRetryPolicy(max_attempts=3),
    )

    assert calls[0]["target_status"] == "failed"
    assert frontier.error_code == "NODE_TIMEOUT"
    assert frontier.error_message == "node timed out"
