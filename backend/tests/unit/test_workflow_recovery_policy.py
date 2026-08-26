"""Workflow Durable Resume 自动恢复策略单元测试。

职责：验证自动恢复的状态、ownership、Checkpoint、冷却窗口和最大次数规则。
边界：纯规则测试，不连接数据库、不启动 Worker、不调用 Runtime。
关键依赖：WorkflowExecutionRecoveryPolicyEvaluator。
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.workflow.checkpoint.recovery.policy import (
    WorkflowExecutionRecoveryPolicy,
    WorkflowExecutionRecoveryPolicyEvaluator,
)


@pytest.fixture
def evaluator() -> WorkflowExecutionRecoveryPolicyEvaluator:
    return WorkflowExecutionRecoveryPolicyEvaluator(
        WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=60)
    )


def test_failed_execution_with_valid_checkpoint_is_eligible(evaluator) -> None:
    now = datetime(2026, 8, 26, 12, 2, tzinfo=UTC)
    decision = evaluator.evaluate(
        execution_status="failed",
        worker_owner=None,
        checkpoint_eligible=True,
        resume_attempt_count=0,
        ended_at=now - timedelta(seconds=61),
        now=now,
    )

    assert decision.eligible is True
    assert decision.reason_code == "eligible"


def test_active_worker_ownership_blocks_automatic_recovery(evaluator) -> None:
    decision = evaluator.evaluate(
        execution_status="failed",
        worker_owner="worker:active",
        checkpoint_eligible=True,
        resume_attempt_count=0,
        ended_at=datetime(2026, 8, 26, 12, 0),
        now=datetime(2026, 8, 26, 12, 2),
    )

    assert decision.eligible is False
    assert decision.reason_code == "worker_ownership_active"


def test_cooldown_prevents_scheduler_polling_from_repeating_resume(evaluator) -> None:
    ended_at = datetime(2026, 8, 26, 12, 1)
    decision = evaluator.evaluate(
        execution_status="failed",
        worker_owner=None,
        checkpoint_eligible=True,
        resume_attempt_count=0,
        ended_at=ended_at,
        now=datetime(2026, 8, 26, 12, 1, 30),
    )

    assert decision.eligible is False
    assert decision.reason_code == "recovery_cooldown_active"
    assert decision.retry_after == datetime(2026, 8, 26, 12, 2)


def test_max_recovery_attempts_stop_automatic_recovery(evaluator) -> None:
    decision = evaluator.evaluate(
        execution_status="failed",
        worker_owner=None,
        checkpoint_eligible=True,
        resume_attempt_count=3,
        ended_at=datetime(2026, 8, 26, 11, 0),
        now=datetime(2026, 8, 26, 12, 0),
    )

    assert decision.eligible is False
    assert decision.reason_code == "max_recovery_attempts_reached"


def test_manual_resume_policy_can_be_disabled_without_changing_candidate_rules() -> None:
    evaluator = WorkflowExecutionRecoveryPolicyEvaluator(
        WorkflowExecutionRecoveryPolicy(max_attempts=0, cooldown_seconds=0)
    )
    decision = evaluator.evaluate(
        execution_status="failed",
        worker_owner=None,
        checkpoint_eligible=True,
        resume_attempt_count=0,
        ended_at=None,
        now=datetime(2026, 8, 26, 12, 0),
    )

    assert decision.eligible is False
    assert decision.reason_code == "automatic_recovery_disabled"


def test_negative_attempt_count_is_rejected(evaluator) -> None:
    with pytest.raises(ValueError, match="不能为负数"):
        evaluator.evaluate(
            execution_status="failed",
            worker_owner=None,
            checkpoint_eligible=True,
            resume_attempt_count=-1,
            ended_at=None,
        )
