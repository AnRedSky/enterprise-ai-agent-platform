"""Workflow Durable Resume HTTP Contract 单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.api.v1.workflows import executions as executions_api


class _FakeExecution:
    id = uuid4(); tenant_id = uuid4(); workflow_id = uuid4(); workflow_version_id = uuid4(); created_by = uuid4()
    retry_of_execution_id = None; resume_of_execution_id = uuid4(); resume_checkpoint_sequence = 2
    idempotency_key = "resume:test"; status = "pending"; current_node_id = None
    input_data = {"content": "checkpoint"}; output_data = None; error_code = None; error_message = None
    started_at = None; ended_at = None; created_at = None


class _FakeDb:
    async def commit(self): return None
    async def refresh(self, _execution): return None


class _FakeService:
    def __init__(self, db): self.db = db; self.get_calls = []; self.resume_calls = []
    async def get(self, execution_id, tenant_id, actor_id, admin):
        self.get_calls.append((execution_id, tenant_id, actor_id, admin)); return _FakeExecution()
    async def resume_from_latest_checkpoint(self, execution, actor_id, *, commit=True):
        self.resume_calls.append((execution, actor_id, commit)); return _FakeExecution()


@pytest.mark.asyncio
async def test_resume_execution_delegates_to_domain_service(monkeypatch) -> None:
    fake_service = _FakeService(db=_FakeDb())
    monkeypatch.setattr(executions_api, "WorkflowExecutionService", lambda db: fake_service)
    execution_id = uuid4(); tenant_id = uuid4(); actor_id = uuid4()
    result = await executions_api.resume_execution(execution_id=execution_id, claims={"tenant_id": str(tenant_id), "sub": str(actor_id), "roles": ["user"]}, db=fake_service.db)
    assert result["status"] == "pending"; assert result["resume_of_execution_id"] == _FakeExecution.resume_of_execution_id; assert result["resume_checkpoint_sequence"] == 2
    assert fake_service.get_calls == [(execution_id, tenant_id, actor_id, False)]; assert len(fake_service.resume_calls) == 1
    resumed_execution, resumed_actor, commit = fake_service.resume_calls[0]
    assert isinstance(resumed_execution, _FakeExecution); assert resumed_actor == actor_id; assert commit is False


def test_resume_route_uses_post_and_requires_user_or_admin_role() -> None:
    route = next(route for route in executions_api.router.routes if route.path.endswith("/executions/{execution_id}/resume"))
    assert route.methods == {"POST"}
    dependency = route.dependant.dependencies[0].call
    required_roles = next(cell.cell_contents for cell in dependency.__closure__ if cell.cell_contents == ("user", "admin"))
    assert required_roles == ("user", "admin")
