"""Workflow Durable Resume 自动恢复领域服务单元测试。

职责：验证 Recovery Policy 与 Checkpoint Candidate 的领域编排，不验证真实数据库或 Worker。
边界：禁止启动 Runtime；通过替换只读依赖验证 eligible / rejected Contract。
关键依赖：WorkflowExecutionAutomaticRecoveryService。
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.automatic import WorkflowExecutionAutomaticRecoveryService
from app.services.workflow.checkpoint.recovery.policy import WorkflowExecutionRecoveryPolicy


@pytest.mark.asyncio
async def test_evaluate_uses_resume_lineage_count_and_checkpoint_candidate(monkeypatch) -> None:
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(),
        policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0),
    )
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_version_id=uuid4(),
        status="failed",
        worker_owner=None,
        ended_at=datetime(2026, 8, 26, 11, 0),
        resume_of_execution_id=None,
    )
    checkpoint = SimpleNamespace(
        id=uuid4(),
        sequence=2,
        node_id="node-a",
        checkpoint_reason="node.completed",
        execution_status="running",
        node_status="completed",
        state_data={"value": 1},
        input_data={},
        output_data={"value": 1},
    )

    async def fake_latest(execution_id):
        assert execution_id == execution.id
        return checkpoint

    async def fake_count(execution_item):
        assert execution_item is execution
        return 2

    monkeypatch.setattr(service.checkpoint, "latest", fake_latest)
    monkeypatch.setattr(service, "_count_resume_ancestors", fake_count)

    result = await service.evaluate(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.decision.eligible is True
    assert result.decision.reason_code == "eligible"
    assert result.decision.attempt_count == 2
    assert result.resume_execution_id is None


@pytest.mark.asyncio
async def test_evaluate_rejects_active_worker_before_automatic_resume() -> None:
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(),
        policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0),
    )
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_version_id=uuid4(),
        status="failed",
        worker_owner="worker:active",
        ended_at=datetime(2026, 8, 26, 11, 0),
        resume_of_execution_id=None,
    )

    result = await service.evaluate(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.decision.eligible is False
    assert result.decision.reason_code == "worker_ownership_active"
