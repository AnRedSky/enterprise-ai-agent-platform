"""Durable Frontier Runtime 异常收敛单元测试。

职责：验证异常分类与 Retry Policy 配置边界，不复制生产 Runtime 执行算法。
"""

from types import SimpleNamespace

from fastapi import HTTPException

from app.services.workflow_worker.durable_frontier_execution import PlannerDrivenDurableFrontierWorkflowWorker


def test_transient_http_failure_is_retryable():
    retryable, code, message = PlannerDrivenDurableFrontierWorkflowWorker._classify_failure(
        HTTPException(503, "provider unavailable")
    )

    assert retryable is True
    assert code == "WORKFLOW_HTTP_503"
    assert message == "provider unavailable"


def test_contract_http_failure_is_terminal():
    retryable, code, message = PlannerDrivenDurableFrontierWorkflowWorker._classify_failure(
        HTTPException(409, "planner frontier mismatch")
    )

    assert retryable is False
    assert code == "WORKFLOW_HTTP_409"
    assert message == "planner frontier mismatch"


def test_retry_policy_uses_runtime_retry_budget():
    version = SimpleNamespace(
        definition={
            "config": {
                "retry_budget": {
                    "max_retries": 2,
                    "base_delay_seconds": 3,
                    "max_delay_seconds": 20,
                }
            }
        }
    )

    policy = PlannerDrivenDurableFrontierWorkflowWorker._retry_policy(version)

    assert policy.max_attempts == 3
    assert policy.base_delay_seconds == 3
    assert policy.max_delay_seconds == 20
