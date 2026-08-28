"""Durable Frontier stale Worker completion 的 Unit Test Contract。"""

from pathlib import Path


REPOSITORY_PATH = Path(__file__).parents[2] / "app" / "services" / "workflow" / "frontier_repository.py"


def test_frontier_transition_requires_unexpired_worker_lease() -> None:
    """Frontier terminal transition 必须同时校验当前 Worker lease 仍然有效。"""
    source = REPOSITORY_PATH.read_text(encoding="utf-8")
    section = source.split("async def transition_owned_frontier", 1)[1]
    assert "WorkflowFrontier.worker_lease_expires_at.is_not(None)" in section
    assert "WorkflowFrontier.worker_lease_expires_at > now" in section


def test_stale_worker_transition_error_mentions_lease_fencing() -> None:
    """stale Worker 被拒绝时错误语义必须明确覆盖 ownership/fencing 失效。"""
    source = REPOSITORY_PATH.read_text(encoding="utf-8")
    assert "ownership or fencing generation mismatch" in source


def test_transition_keeps_database_lock_and_attempt_fencing() -> None:
    """Lease fencing 不得替代已有的行锁与 Frontier attempt fencing。"""
    source = REPOSITORY_PATH.read_text(encoding="utf-8")
    section = source.split("async def transition_owned_frontier", 1)[1]
    assert "WorkflowFrontier.attempt == attempt" in section
    assert ".with_for_update()" in section
