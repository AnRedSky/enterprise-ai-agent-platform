"""Agent Delegation timeout 运行时规则单元测试。

验证 Delegation timeout 与 Workflow Runtime timeout 的最短边界，以及 timeout 后不影响父 Execution 的契约。
"""

from datetime import datetime, timedelta

import pytest

from app.services.agent_delegation.timeout import effective_runtime_timeout_seconds, remaining_timeout_seconds


NOW = datetime(2026, 8, 28, 16, 0, 0)


def test_remaining_timeout_is_inclusive_at_boundary() -> None:
    timeout_at = NOW + timedelta(seconds=5)
    assert remaining_timeout_seconds(timeout_at, now=NOW) == 5
    assert remaining_timeout_seconds(timeout_at, now=timeout_at) == 0
    assert remaining_timeout_seconds(timeout_at, now=timeout_at + timedelta(seconds=1)) == 0
    assert remaining_timeout_seconds(None, now=NOW) is None


def test_delegation_timeout_wins_when_shorter_than_workflow_runtime() -> None:
    timeout, delegation_bound = effective_runtime_timeout_seconds(
        60,
        NOW + timedelta(seconds=3),
        now=NOW,
    )
    assert timeout == 3
    assert delegation_bound is True


def test_workflow_timeout_wins_when_delegation_has_more_budget() -> None:
    timeout, delegation_bound = effective_runtime_timeout_seconds(
        10,
        NOW + timedelta(seconds=30),
        now=NOW,
    )
    assert timeout == 10
    assert delegation_bound is False


def test_missing_delegation_timeout_keeps_workflow_timeout() -> None:
    timeout, delegation_bound = effective_runtime_timeout_seconds(10, None, now=NOW)
    assert timeout == 10
    assert delegation_bound is False


def test_non_positive_workflow_timeout_is_rejected() -> None:
    with pytest.raises(ValueError):
        effective_runtime_timeout_seconds(0, NOW + timedelta(seconds=1), now=NOW)
