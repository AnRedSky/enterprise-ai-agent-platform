from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.agent_delegation.identity import delegation_identity_key, validate_budget


def test_delegation_identity_is_stable_and_scoped() -> None:
    tenant_id = uuid4()
    execution_id = uuid4()
    first = delegation_identity_key(tenant_id=tenant_id, source_execution_id=execution_id, delegation_key=" task-a ")
    second = delegation_identity_key(tenant_id=tenant_id, source_execution_id=execution_id, delegation_key="task-a")
    assert first == second
    assert str(tenant_id) in first
    assert str(execution_id) in first


@pytest.mark.parametrize(
    ("field", "value"),
    [("max_delegation_depth", 0), ("max_active_delegations", 0), ("timeout_seconds", 0)],
)
def test_budget_rejects_invalid_bounds(field: str, value: int) -> None:
    values = {"max_delegation_depth": 3, "max_active_delegations": 4, "timeout_seconds": 300, "model_budget": {}}
    values[field] = value
    with pytest.raises(HTTPException) as exc:
        validate_budget(**values)
    assert exc.value.status_code == 422


def test_budget_accepts_governed_values() -> None:
    result = validate_budget(max_delegation_depth=3, max_active_delegations=4, timeout_seconds=300, model_budget={"max_tokens": 2048, "cost_limit": 2.5})
    assert result == (3, 4, 300, {"max_tokens": 2048, "cost_limit": 2.5})


def test_identity_rejects_blank_key() -> None:
    with pytest.raises(HTTPException) as exc:
        delegation_identity_key(tenant_id=uuid4(), source_execution_id=uuid4(), delegation_key=" ")
    assert exc.value.status_code == 422
