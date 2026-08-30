"""Operator Action Governance Contract 单元测试。

职责：验证统一操作定义、状态可用性、高风险确认与幂等键边界。
边界：不启动服务、不访问数据库，不复制生产状态机算法。
"""

import pytest
from fastapi import HTTPException

from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


@pytest.mark.parametrize(
    ("status", "action", "expected"),
    [
        ("pending", "run", True),
        ("pending", "cancel", True),
        ("running", "cancel", True),
        ("failed", "retry", True),
        ("completed", "run", False),
        ("completed", "cancel", False),
        ("running", "retry", False),
    ],
)
def test_execution_action_availability(status, action, expected):
    result = OperatorActionGovernanceService.availability("workflow_execution", action, status)
    assert result["allowed"] is expected
    assert result["reason_code"] == ("AVAILABLE" if expected else "INVALID_EXECUTION_STATE")


def test_high_risk_execution_action_requires_confirmation():
    with pytest.raises(HTTPException) as exc_info:
        OperatorActionGovernanceService.validate_request(
            "workflow_execution", "cancel", confirm=False, idempotency_key=None,
        )
    assert exc_info.value.status_code == 400


def test_retry_requires_idempotency_key():
    with pytest.raises(HTTPException) as exc_info:
        OperatorActionGovernanceService.validate_request(
            "workflow_execution", "retry", confirm=True, idempotency_key=None,
        )
    assert exc_info.value.status_code == 400


def test_trigger_invoke_is_only_available_for_enabled_manual_trigger():
    assert OperatorActionGovernanceService.availability(
        "workflow_trigger", "invoke", "enabled", trigger_type="manual",
    )["allowed"] is True
    assert OperatorActionGovernanceService.availability(
        "workflow_trigger", "invoke", "enabled", trigger_type="scheduled",
    )["allowed"] is False
    assert OperatorActionGovernanceService.availability(
        "workflow_trigger", "invoke", "disabled", trigger_type="manual",
    )["allowed"] is False


def test_trigger_enable_disable_are_state_directed():
    assert OperatorActionGovernanceService.availability(
        "workflow_trigger", "enable", "disabled", trigger_type="manual",
    )["allowed"] is True
    assert OperatorActionGovernanceService.availability(
        "workflow_trigger", "disable", "enabled", trigger_type="manual",
    )["allowed"] is True
    assert OperatorActionGovernanceService.availability(
        "workflow_trigger", "enable", "enabled", trigger_type="manual",
    )["allowed"] is False


def test_unknown_operator_action_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        OperatorActionGovernanceService.definition("workflow_execution", "purge")
    assert exc_info.value.status_code == 404


def test_all_high_risk_actions_require_confirmation():
    for resource_type, action in (
        ("workflow_execution", "cancel"),
        ("workflow_execution", "retry"),
        ("workflow_execution", "resume"),
        ("workflow_trigger", "enable"),
        ("workflow_trigger", "disable"),
        ("workflow_trigger", "delete"),
    ):
        definition = OperatorActionGovernanceService.definition(resource_type, action)
        assert definition.requires_confirmation is True


def test_retry_and_trigger_invoke_require_idempotency_key():
    assert OperatorActionGovernanceService.definition(
        "workflow_execution", "retry",
    ).requires_idempotency_key is True
    assert OperatorActionGovernanceService.definition(
        "workflow_trigger", "invoke",
    ).requires_idempotency_key is True
