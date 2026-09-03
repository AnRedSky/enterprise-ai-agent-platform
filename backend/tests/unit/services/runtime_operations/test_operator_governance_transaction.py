"""Operator Governance Execution 事务边界单元测试。

职责：验证 Execution / Trigger 运维动作与 Operator Audit、幂等事实共享单一提交边界，并验证最终化失败时事务能够回滚。
边界：不访问真实数据库、不启动服务、不复制 Workflow Execution 状态机。
关键依赖：OperatorActionGovernanceService、WorkflowExecutionService、WorkflowTriggerService。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.runtime_operations import operator_governance as governance_module
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


def _execution(status: str = "pending") -> SimpleNamespace:
    """创建最小 Operator Governance Execution 测试事实。"""
    execution_id = uuid4()
    workflow_id = uuid4()
    version_id = uuid4()
    actor_id = uuid4()
    return SimpleNamespace(
        id=execution_id,
        workflow_id=workflow_id,
        workflow_version_id=version_id,
        created_by=actor_id,
        status=status,
    )


def _db_mock() -> SimpleNamespace:
    """创建仅包含本测试实际事务边界所需异步操作的数据库替身，避免隐式 AsyncMock 产生未等待协程。"""
    return SimpleNamespace(
        execute=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_run_is_deferred_until_operator_audit_transaction(monkeypatch):
    """Run 不得在领域服务内部提前提交，Operator Audit 完成后才统一 commit。"""
    db = _db_mock()
    service = OperatorActionGovernanceService(db)
    execution = _execution()
    version = SimpleNamespace(id=execution.workflow_version_id)
    result = SimpleNamespace(id=uuid4())

    service._execution = AsyncMock(return_value=execution)
    service.availability = Mock(return_value={"allowed": True})
    service._audit = AsyncMock()

    workflow_service = SimpleNamespace(run=AsyncMock(return_value=result))
    monkeypatch.setattr(governance_module, "WorkflowExecutionService", Mock(return_value=workflow_service))
    db.execute.return_value.scalar_one_or_none.return_value = version

    persisted = await service.execute_execution(execution.id, uuid4(), uuid4(), True, "run")

    assert persisted is result
    workflow_service.run.assert_awaited_once()
    assert workflow_service.run.await_args.kwargs["commit"] is False
    service._audit.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    db.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_cancel_is_deferred_until_operator_audit_transaction(monkeypatch):
    """Cancel 不得先提交 Execution 状态，必须与 Operator Audit 共用事务。"""
    db = _db_mock()
    service = OperatorActionGovernanceService(db)
    execution = _execution(status="running")
    result = SimpleNamespace(id=execution.id)

    service._execution = AsyncMock(return_value=execution)
    service.availability = Mock(return_value={"allowed": True})
    service._audit = AsyncMock()

    workflow_service = SimpleNamespace(cancel=AsyncMock(return_value=result))
    monkeypatch.setattr(governance_module, "WorkflowExecutionService", Mock(return_value=workflow_service))

    persisted = await service.execute_execution(
        execution.id, uuid4(), uuid4(), True, "cancel", confirm=True, reason="operator test"
    )

    assert persisted is result
    workflow_service.cancel.assert_awaited_once()
    assert workflow_service.cancel.await_args.kwargs["commit"] is False
    service._audit.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    db.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_run_does_not_commit_when_operator_audit_fails(monkeypatch):
    """Operator Audit 失败时不得提交已经产生的 Execution 状态变更。"""
    db = _db_mock()
    service = OperatorActionGovernanceService(db)
    execution = _execution()
    version = SimpleNamespace(id=execution.workflow_version_id)
    result = SimpleNamespace(id=uuid4())

    service._execution = AsyncMock(return_value=execution)
    service.availability = Mock(return_value={"allowed": True})
    service._audit = AsyncMock(side_effect=RuntimeError("audit failure"))

    workflow_service = SimpleNamespace(run=AsyncMock(return_value=result))
    monkeypatch.setattr(governance_module, "WorkflowExecutionService", Mock(return_value=workflow_service))
    db.execute.return_value.scalar_one_or_none.return_value = version

    with pytest.raises(RuntimeError, match="audit failure"):
        await service.execute_execution(execution.id, uuid4(), uuid4(), True, "run")

    assert workflow_service.run.await_args.kwargs["commit"] is False
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_rolls_back_when_operator_audit_fails(monkeypatch):
    """Cancel 已修改 Execution 后若最终 Audit 失败，必须回滚当前治理事务。"""
    db = _db_mock()
    service = OperatorActionGovernanceService(db)
    execution = _execution(status="running")
    result = SimpleNamespace(id=execution.id)

    service._execution = AsyncMock(return_value=execution)
    service.availability = Mock(return_value={"allowed": True})
    service._audit = AsyncMock(side_effect=RuntimeError("audit failure"))

    workflow_service = SimpleNamespace(cancel=AsyncMock(return_value=result))
    monkeypatch.setattr(governance_module, "WorkflowExecutionService", Mock(return_value=workflow_service))

    with pytest.raises(RuntimeError, match="audit failure"):
        await service.execute_execution(
            execution.id, uuid4(), uuid4(), True, "cancel", confirm=True, reason="operator test"
        )

    assert workflow_service.cancel.await_args.kwargs["commit"] is False
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_rolls_back_when_final_commit_fails(monkeypatch):
    """最终数据库提交失败时必须显式回滚连接上的未提交领域状态。"""
    db = _db_mock()
    db.commit.side_effect = RuntimeError("commit failure")
    service = OperatorActionGovernanceService(db)
    execution = _execution()
    version = SimpleNamespace(id=execution.workflow_version_id)
    result = SimpleNamespace(id=uuid4())

    service._execution = AsyncMock(return_value=execution)
    service.availability = Mock(return_value={"allowed": True})
    service._audit = AsyncMock()

    workflow_service = SimpleNamespace(run=AsyncMock(return_value=result))
    monkeypatch.setattr(governance_module, "WorkflowExecutionService", Mock(return_value=workflow_service))
    db.execute.return_value.scalar_one_or_none.return_value = version

    with pytest.raises(RuntimeError, match="commit failure"):
        await service.execute_execution(execution.id, uuid4(), uuid4(), True, "run")

    service._audit.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.rollback.assert_awaited_once()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_trigger_enable_rolls_back_when_operator_audit_fails(monkeypatch):
    """Trigger 状态变更后若治理 Audit 失败，必须回滚 Trigger 与 Audit 的同一事务。"""
    db = _db_mock()
    service = OperatorActionGovernanceService(db)
    trigger = SimpleNamespace(id=uuid4(), workflow_id=uuid4(), status="disabled", trigger_type="manual")
    workflow = SimpleNamespace(id=trigger.workflow_id)

    service._trigger = AsyncMock(return_value=(workflow, trigger))
    service.availability = Mock(return_value={"allowed": True})
    service._audit = AsyncMock(side_effect=RuntimeError("audit failure"))

    trigger_service = SimpleNamespace(update=AsyncMock(return_value=trigger))
    monkeypatch.setattr(governance_module, "WorkflowTriggerService", Mock(return_value=trigger_service))

    with pytest.raises(RuntimeError, match="audit failure"):
        await service.execute_trigger(
            trigger.id, uuid4(), uuid4(), True, "enable", confirm=True
        )

    trigger_service.update.assert_awaited_once_with(trigger, None, "enabled", None, commit=False)
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()
