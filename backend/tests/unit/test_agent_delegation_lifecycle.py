"""Agent Delegation 生命周期与 fencing 规则单元测试。

验证范围：状态转换、终态封闭、Worker generation fencing 与 timeout 边界。
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.services.agent_delegation.lifecycle import (
    is_timeout_due,
    validate_transition,
    validate_worker_fence,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("pending", "running"),
        ("pending", "cancelled"),
        ("running", "completed"),
        ("running", "failed"),
        ("running", "timed_out"),
        ("running", "cancelled"),
    ],
)
def test_validate_transition_accepts_contract_transitions(current: str, target: str) -> None:
    validate_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("completed", "running"),
        ("failed", "running"),
        ("timed_out", "completed"),
        ("cancelled", "running"),
        ("pending", "completed"),
        ("running", "pending"),
    ],
)
def test_validate_transition_rejects_terminal_or_invalid_transitions(current: str, target: str) -> None:
    with pytest.raises(ValueError):
        validate_transition(current, target)


def test_validate_worker_fence_accepts_current_worker_generation() -> None:
    worker_id = uuid4()
    validate_worker_fence(
        status="running",
        worker_execution_id=worker_id,
        expected_worker_execution_id=worker_id,
    )


@pytest.mark.parametrize("status", ["pending", "completed", "failed", "timed_out", "cancelled"])
def test_validate_worker_fence_rejects_non_running_status(status: str) -> None:
    with pytest.raises(ValueError):
        validate_worker_fence(
            status=status,
            worker_execution_id=uuid4(),
            expected_worker_execution_id=uuid4(),
        )


def test_validate_worker_fence_rejects_missing_or_stale_worker() -> None:
    current = uuid4()
    stale = uuid4()

    with pytest.raises(ValueError):
        validate_worker_fence(
            status="running",
            worker_execution_id=None,
            expected_worker_execution_id=current,
        )

    with pytest.raises(ValueError):
        validate_worker_fence(
            status="running",
            worker_execution_id=current,
            expected_worker_execution_id=stale,
        )


def test_is_timeout_due_uses_inclusive_boundary() -> None:
    timeout_at = datetime(2026, 8, 28, 16, 0, 0)
    assert is_timeout_due(timeout_at, now=timeout_at) is True
    assert is_timeout_due(timeout_at, now=timeout_at - timedelta(microseconds=1)) is False
    assert is_timeout_due(timeout_at, now=timeout_at + timedelta(microseconds=1)) is True
    assert is_timeout_due(None, now=timeout_at) is False
