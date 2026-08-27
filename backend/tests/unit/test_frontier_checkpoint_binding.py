from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontier_completion_checkpoint_is_bound_to_source_frontier():
    source = (ROOT / "app/services/workflow/frontier_progression.py").read_text(encoding="utf-8")
    assert "frontier_id=frontier.id if checkpoint_reason == \"frontier_completed\" else None" in source


def test_frontier_completion_idempotency_is_scoped_to_source_frontier():
    source = (ROOT / "app/services/workflow/frontier_progression.py").read_text(encoding="utf-8")
    assert "WorkflowExecutionCheckpoint.frontier_id == current.id" in source


def test_checkpoint_service_requires_frontier_for_frontier_completion():
    source = (ROOT / "app/services/workflow/checkpoint/service.py").read_text(encoding="utf-8")
    assert 'checkpoint_reason == "frontier_completed" and frontier_id is None' in source
    assert 'checkpoint_reason != "frontier_completed" and frontier_id is not None' in source


def test_checkpoint_model_declares_frontier_foreign_key():
    source = (ROOT / "app/models/workflow_checkpoint.py").read_text(encoding="utf-8")
    assert "frontier_id" in source
    assert 'ForeignKey("workflow_frontiers.id", ondelete="SET NULL")' in source
