from __future__ import annotations

import inspect
from pathlib import Path

from app.services.workflow.execution import WorkflowExecutionService


def test_transition_node_exposes_explicit_commit_ownership() -> None:
    parameter = inspect.signature(WorkflowExecutionService.transition_node).parameters["commit"]
    assert parameter.default is True
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_runtime_node_transitions_are_caller_owned() -> None:
    source = Path("app/runtime/workflow/runtime.py").read_text(encoding="utf-8")
    assert 'target_status="completed"' not in source
    assert 'output_data=output, commit=False' in source
    assert 'input_data=current_data, commit=False' in source
