"""Durable Frontier progression 与 Execution Worker epoch 的 Unit Test Contract。"""

from pathlib import Path


REPOSITORY_PATH = Path(__file__).parents[2] / "app" / "services" / "workflow" / "frontier_progression.py"


def _source() -> str:
    return REPOSITORY_PATH.read_text(encoding="utf-8")


def test_progression_distinguishes_frontier_attempt_from_execution_worker_epoch() -> None:
    source = _source()
    assert "`attempt` 只代表 Frontier consumption attempt" in source
    assert "Execution 的 `worker_attempt` 是独立的" in source


def test_progression_locks_execution_before_durable_completion() -> None:
    source = _source()
    section = source.split("async def complete_frontier_with_checkpoint", 1)[1]
    assert "select(WorkflowExecution)" in section
    assert ".with_for_update()" in section
    assert "execution.worker_owner != worker_owner" in section
    assert "execution.worker_lease_expires_at <= now" in section


def test_next_frontier_checkpoint_uses_execution_worker_epoch() -> None:
    source = _source()
    section = source.split("checkpoint = await checkpoint_service.append_next_in_transaction", 1)[1]
    assert "expected_worker_attempt=execution_worker_attempt if next_identity is not None else None" in section
    assert "expected_worker_owner=worker_owner if next_identity is not None else None" in section


def test_frontier_attempt_is_not_used_as_execution_worker_epoch() -> None:
    source = _source()
    section = source.split("async def complete_frontier_with_checkpoint", 1)[1]
    assert "expected_worker_attempt=attempt" not in section
