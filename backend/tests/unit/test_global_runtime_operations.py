from __future__ import annotations

import uuid

import pytest
from sqlalchemy.dialects import postgresql

from app.services.runtime_operations.global_operations import GlobalRuntimeOperationsService


def test_global_runtime_window_is_bounded() -> None:
    hours, since = GlobalRuntimeOperationsService._window(999)

    assert hours == 168
    assert since.tzinfo is None


def test_global_runtime_counts_are_normalized() -> None:
    assert GlobalRuntimeOperationsService._counts([("running", 2), ("failed", 1)]) == {
        "running": 2,
        "failed": 1,
    }


def test_global_runtime_agent_filter_uses_workflow_version_definition() -> None:
    agent_id = uuid.uuid4()
    expression = GlobalRuntimeOperationsService._agent_filter(agent_id)
    compiled = str(expression.compile(dialect=postgresql.dialect()))

    assert "workflow_version_id" in compiled
    assert "agent_id" in compiled


def test_global_runtime_agent_filter_is_optional() -> None:
    assert GlobalRuntimeOperationsService._agent_filter(None) is None


@pytest.mark.parametrize("window_hours", [0, -1])
def test_global_runtime_window_never_returns_non_positive(window_hours: int) -> None:
    hours, _ = GlobalRuntimeOperationsService._window(window_hours)

    assert hours == 1
