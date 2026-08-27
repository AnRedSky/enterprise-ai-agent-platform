"""Durable Frontier Recovery re-entry 的 Unit Test Contract。"""

from pathlib import Path


RUNTIME_PATH = Path(__file__).parents[2] / "app" / "services" / "workflow_worker" / "frontier_runtime.py"
REPOSITORY_PATH = Path(__file__).parents[2] / "app" / "services" / "workflow" / "frontier_repository.py"


def test_recovered_execution_reuses_current_worker_epoch_for_pending_frontier() -> None:
    """Recovery 后同一 Execution 的后续 Frontier 不应因 pending 状态被当前 owner 阻塞。"""
    source = RUNTIME_PATH.read_text(encoding="utf-8")
    assert 'execution.status == "pending" and owned_by_current_worker' in source
    assert "execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)" in source


def test_pending_current_owner_is_claim_eligible() -> None:
    """Repository Claim predicate 必须与 Worker candidate predicate 保持同一 eligibility。"""
    source = REPOSITORY_PATH.read_text(encoding="utf-8")
    assert 'WorkflowExecution.status == "pending"' in source
    assert "WorkflowExecution.worker_owner == worker_owner" in source


def test_recovery_does_not_clear_execution_owner_implicitly() -> None:
    """Recovery 只释放 Frontier 调度权，Execution ownership 由后续 Claim 事务重新建立/复用。"""
    source = REPOSITORY_PATH.read_text(encoding="utf-8")
    recovery_section = source.split("async def recover_expired_frontiers", 1)[1].split(
        "async def transition_owned_frontier", 1
    )[0]
    assert "frontier.worker_owner = None" in recovery_section
    assert "execution.worker_owner = None" not in recovery_section
