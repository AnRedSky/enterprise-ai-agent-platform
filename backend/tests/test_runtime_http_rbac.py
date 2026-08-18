from uuid import UUID, uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.runtime import _runtime_claims, router as runtime_router
from app.main import app
from app.schemas.runtime import ExecutionItem


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


def test_execution_item_maps_orm_id_to_execution_id():
    execution_id = uuid4()

    class ExecutionRow:
        id = execution_id
        request_id = "req"
        trace_id = "trace"
        session_id = None
        agent_id = uuid4()
        agent_version = "1.0.0"
        model_id = "mock-model"
        status = "success"
        from datetime import datetime
        started_at = datetime(2026, 8, 18, 10, 0, 0)
        ended_at = None
        duration_ms = 1
        error_code = None

    item = ExecutionItem.model_validate(ExecutionRow(), from_attributes=True)
    assert item.execution_id == execution_id
    assert item.model_dump()["execution_id"] == execution_id


def test_runtime_requires_bearer_authentication():
    response = TestClient(app).get("/api/v1/runtime/executions")
    assert response.status_code == 401


def test_runtime_claims_forwards_resolved_bearer_credentials(monkeypatch):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")
    expected = {"sub": str(uuid4()), "roles": ["user"]}
    captured = {}

    def fake_current_claims(received):
        captured["credentials"] = received
        return expected

    monkeypatch.setattr("app.api.runtime.current_claims", fake_current_claims)
    assert _runtime_claims(credentials) == expected
    assert captured["credentials"] is credentials


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
