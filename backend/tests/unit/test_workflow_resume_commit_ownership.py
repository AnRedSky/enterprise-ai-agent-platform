"""Durable Resume commit ownership 单元测试。"""

import inspect

from app.services.workflow.execution import WorkflowExecutionService


def test_resume_service_exposes_explicit_commit_ownership():
    signature = inspect.signature(WorkflowExecutionService.resume_from_latest_checkpoint)

    assert signature.parameters["commit"].default is True


def test_resume_service_does_not_commit_when_caller_owns_transaction():
    source = inspect.getsource(WorkflowExecutionService.resume_from_latest_checkpoint)

    assert "if commit:" in source
    assert "await self.db.commit()" in source
    assert "await self.db.refresh(resume_execution)" in source
