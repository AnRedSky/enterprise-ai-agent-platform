from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.runtime import router as runtime_router
from app.main import app


def _install_db_override():
    async def fake_db():
        yield None
    app.dependency_overrides[get_db] = fake_db


def _remove_db_override():
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_overrides():
    _remove_db_override()
    yield
    _remove_db_override()


def test_runtime_requires_bearer_authentication():
    response = TestClient(app).get("/api/v1/runtime/executions")
    assert response.status_code == 401


def test_runtime_owner_scope_returns_404_for_inaccessible_execution(monkeypatch):
    actor_id = uuid4()
    execution_id = uuid4()
    _install_db_override()
    monkeypatch.setattr("app.api.runtime.current_claims", lambda: {"sub": str(actor_id), "roles": ["user"]})

    async def inaccessible(self, actor, is_admin, requested_id):
        assert actor == actor_id
        assert is_admin is False
        assert requested_id == execution_id
        return None

    monkeypatch.setattr("app.api.runtime.RuntimeQueryService.execution", inaccessible)
    response = TestClient(app).get(f"/api/v1/runtime/executions/{execution_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "execution not found"


def test_runtime_admin_scope_can_query_cross_owner_execution(monkeypatch):
    actor_id = uuid4()
    execution_id = uuid4()
    _install_db_override()
    monkeypatch.setattr("app.api.runtime.current_claims", lambda: {"sub": str(actor_id), "roles": ["admin"]})
    execution = {"execution_id": execution_id, "request_id": "req", "trace_id": "trace", "agent_id": uuid4(), "status": "success"}

    async def accessible(self, actor, is_admin, requested_id):
        assert actor == actor_id
        assert is_admin is True
        assert requested_id == execution_id
        return execution

    monkeypatch.setattr("app.api.runtime.RuntimeQueryService.execution", accessible)
    response = TestClient(app).get(f"/api/v1/runtime/executions/{execution_id}")
    assert response.status_code == 200
    assert response.json()["execution"]["status"] == "success"


def test_runtime_filters_are_forwarded_to_query_service(monkeypatch):
    actor_id = uuid4()
    agent_id = uuid4()
    _install_db_override()
    monkeypatch.setattr("app.api.runtime.current_claims", lambda: {"sub": str(actor_id), "roles": ["user"]})
    captured = {}

    async def executions(self, *args):
        captured["args"] = args
        return 1, 20, 0, []

    monkeypatch.setattr("app.api.runtime.RuntimeQueryService.executions", executions)
    response = TestClient(app).get(
        "/api/v1/runtime/executions?page=2&page_size=20&status=failed"
        f"&agent_id={agent_id}&trace_id=trace-x&request_id=req-x"
    )
    assert response.status_code == 200
    args = captured["args"]
    assert args[0] == actor_id and args[1] is False
    assert args[2:6] == (2, 20, "failed", agent_id)
    assert args[6:8] == ("trace-x", "req-x")
