from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_scheduled_trigger_enqueues_durable_frontier() -> None:
    source = _read("app/services/trigger/service.py")
    assert "WorkflowFrontierIdentity" in source
    assert "enqueue_frontier(" in source
    assert '"dispatch_mode": "durable_frontier"' in source


def test_default_worker_uses_durable_frontier_dispatch() -> None:
    source = _read("app/services/workflow_worker/__init__.py")
    assert "WorkflowWorker = DurableFrontierWorkflowWorker" in source


def test_frontier_worker_claims_execution_in_same_transaction() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert "claim_next_frontier(" in source
    assert "WorkflowExecution.worker_owner" in source
    assert "await db.commit()" in source


def test_frontier_worker_preserves_fencing_generation() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert "attempt=frontier.attempt" in source
    assert "transition_owned_frontier(" in source
    assert "renew_owned_frontier_lease(" in source
