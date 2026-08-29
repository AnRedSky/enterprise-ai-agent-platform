"""Workflow Worker 默认入口契约。"""

from app.services.workflow_worker import DurableFrontierWorkflowWorker, WorkflowWorker


def test_default_workflow_worker_uses_canonical_durable_frontier_runtime() -> None:
    """默认 Worker 必须直接复用唯一 Durable Frontier Runtime。"""
    assert WorkflowWorker is DurableFrontierWorkflowWorker
