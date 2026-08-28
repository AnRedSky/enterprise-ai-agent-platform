"""Agent Delegation 预算与身份规则单元测试。

验证范围：稳定幂等身份、预算边界与禁止布尔值混入整数治理参数。
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.agent_delegation.identity import delegation_identity_key, validate_budget


def test_delegation_identity_is_stable_and_tenant_scoped():
    tenant_id = uuid4()
    execution_id = uuid4()

    first = delegation_identity_key(
        tenant_id=tenant_id,
        source_execution_id=execution_id,
        delegation_key="  summarize  ",
    )
    second = delegation_identity_key(
        tenant_id=tenant_id,
        source_execution_id=execution_id,
        delegation_key="summarize",
    )

    assert first == second
    assert str(tenant_id) in first
    assert str(execution_id) in first


def test_delegation_identity_rejects_empty_key():
    with pytest.raises(HTTPException) as exc_info:
        delegation_identity_key(
            tenant_id=uuid4(),
            source_execution_id=uuid4(),
            delegation_key="   ",
        )

    assert exc_info.value.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_delegation_depth", 0),
        ("max_delegation_depth", 21),
        ("max_active_delegations", 0),
        ("max_active_delegations", 101),
        ("timeout_seconds", 0),
        ("timeout_seconds", 86_401),
        ("max_delegation_depth", True),
    ],
)
def test_validate_budget_rejects_out_of_range_values(field, value):
    values = {
        "max_delegation_depth": 3,
        "max_active_delegations": 4,
        "timeout_seconds": 60,
        "model_budget": {"max_tokens": 1000},
    }
    values[field] = value

    with pytest.raises(HTTPException) as exc_info:
        validate_budget(**values)

    assert exc_info.value.status_code == 422


def test_validate_budget_normalizes_model_budget_without_mutation():
    model_budget = {"max_tokens": 1000, "max_cost": 2.5}

    result = validate_budget(
        max_delegation_depth=3,
        max_active_delegations=4,
        timeout_seconds=60,
        model_budget=model_budget,
    )

    assert result == (3, 4, 60, model_budget)
    assert result[3] is not model_budget
