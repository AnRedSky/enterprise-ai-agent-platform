from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_scheduled_trigger_enqueues_durable_frontier() -> None:
    source = _read("app/services/trigger/service.py")
    assert "WorkflowFrontierIdentity" in source
    assert "enqueue_frontier(" in source
    assert '"dispatch_mode": "durable_frontier"' in source


def test_default_worker_uses_planner_driven_durable_frontier_dispatch() -> None:
    source = _read("app/services/workflow_worker/__init__.py")
    assert "WorkflowWorker = PlannerDrivenDurableFrontierWorkflowWorker" in source


def test_frontier_worker_claims_execution_in_same_transaction() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert "claim_next_frontier(" in source
    assert "WorkflowExecution.worker_owner" in source
    assert "await db.commit()" in source


def test_frontier_worker_starts_claimed_pending_execution_in_same_transaction() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert 'if execution.status == "pending":' in source
    assert 'execution.status = "running"' in source
    assert "execution.started_at = now_naive" in source
    assert '"execution.state_changed"' in source


def test_frontier_worker_preserves_fencing_generation() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert "attempt=frontier.attempt" in source
    assert "transition_owned_frontier(" in source
    assert "renew_owned_frontier_lease(" in source


def test_frontier_worker_reuses_owned_running_execution() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert 'execution.status == "running" and owned_by_current_worker' in source
    assert "execution.worker_attempt = int(execution.worker_attempt or 0) + 1" in source
    assert "execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)" in source


def test_expired_foreign_execution_gets_new_fencing_generation() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert 'execution.status == "running" and execution_lease_expired' in source
    assert 'execution.status = "pending"' in source


def test_node_checkpoint_write_carries_execution_fencing_generation() -> None:
    source = _read("app/services/workflow/execution.py")
    assert "expected_worker_owner=execution.worker_owner" in source
    assert "expected_worker_attempt=int(execution.worker_attempt or 0)" in source
    assert "checkpoint.append_next_in_transaction(" in source


def test_frontier_claim_is_execution_state_aware() -> None:
    source = _read("app/services/workflow/frontier_repository.py")
    assert "WorkflowExecution" in source
    assert ".join(" in source
    assert 'WorkflowExecution.status == "pending"' in source or 'WorkflowFrontier.status.in_(("pending", "retry_wait"))' in source
    assert 'WorkflowExecution.status == "running"' in source
    assert "WorkflowExecution.worker_owner == worker_owner" in source


def test_frontier_claim_does_not_block_on_terminal_execution() -> None:
    source = _read("app/services/workflow/frontier_repository.py")
    assert 'WorkflowExecution.status == "completed"' not in source
    assert 'WorkflowExecution.status == "failed"' not in source
    assert 'WorkflowExecution.status == "cancelled"' not in source


def test_frontier_runtime_uses_unified_runtime_entry_contract() -> None:
    source = _read("app/services/workflow_worker/frontier_runtime.py")
    assert "execute_claimed_execution(self, frontier.execution_id)" in source
    assert "runtime_entry" in source


def test_runtime_entry_allows_pending_start_and_owned_running_continuation() -> None:
    source = _read("app/services/workflow_worker/runtime_entry.py")
    assert 'WorkflowExecution.status.in_({"pending", "running"})' in source
    assert 'if execution.status == "pending":' in source
    assert 'elif execution.status == "running":' in source
    assert 'await service.transition(execution, "running"' in source
    assert "WorkflowRuntime(db, execution_service=service)" in source


def test_runtime_entry_preserves_execution_lease_fencing() -> None:
    source = _read("app/services/workflow_worker/runtime_entry.py")
    assert "WorkflowWorkerLeaseGuard" in source
    assert "_renew_with_abort_signal" in source
    assert "WorkflowWorkerLeaseLost" in source
    assert 'reason_code = "WORKER_LEASE_LOST"' in source
