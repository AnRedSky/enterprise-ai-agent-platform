from __future__ import annotations

import inspect

from app.services.workflow.execution import WorkflowExecutionService


def test_transition_node_exposes_explicit_commit_ownership() -> None:
    parameter = inspect.signature(WorkflowExecutionService.transition_node).parameters["commit"]
    assert parameter.default is True
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
