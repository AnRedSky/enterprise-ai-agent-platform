import pytest
from fastapi import HTTPException

from app.runtime.workflow_runtime import WorkflowRuntime


def test_workflow_circuit_breaker_is_opt_in():
    definition = {
        "config": {"timeout_ms": 1000},
        "nodes": [{"id": "input", "type": "input", "config": {}}],
    }
    nodes = WorkflowRuntime.validate_definition(definition)
    assert nodes[0]["id"] == "input"


def test_workflow_circuit_breaker_config_is_validated():
    definition = {
        "config": {"timeout_ms": 1000},
        "nodes": [{
            "id": "agent",
            "type": "agent",
            "config": {
                "agent_id": "00000000-0000-0000-0000-000000000101",
                "circuit_breaker": {"enabled": True, "failure_threshold": 3, "recovery_timeout_ms": 1000},
            },
        }],
    }
    nodes = WorkflowRuntime.validate_definition(definition)
    assert nodes[0]["config"]["circuit_breaker"]["enabled"] is True


def test_workflow_circuit_breaker_rejects_invalid_recovery_window():
    definition = {
        "config": {"timeout_ms": 1000},
        "nodes": [{
            "id": "agent",
            "type": "agent",
            "config": {
                "agent_id": "00000000-0000-0000-0000-000000000101",
                "circuit_breaker": {"enabled": True, "recovery_timeout_ms": 10},
            },
        }],
    }
    with pytest.raises(HTTPException) as exc:
        WorkflowRuntime.validate_definition(definition)
    assert exc.value.status_code == 422


def test_circuit_open_is_not_retryable_by_default():
    assert "CIRCUIT_OPEN" not in WorkflowRuntime.DEFAULT_RETRY_POLICY["retryable_error_codes"]
