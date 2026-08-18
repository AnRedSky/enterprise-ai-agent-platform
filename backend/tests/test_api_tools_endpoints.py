from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.tools import list_tools
from app.main import app

client = TestClient(app)


def test_tool_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/tools")}
    assert ("/api/v1/tools", ("POST",)) in paths
    assert ("/api/v1/tools", ("GET",)) in paths
    assert ("/api/v1/tools/{tool_id}/enable", ("POST",)) in paths
    assert ("/api/v1/tools/{tool_id}/disable", ("POST",)) in paths
    assert ("/api/v1/tools/{tool_id}/bind/{agent_id}", ("POST",)) in paths
    assert ("/api/v1/tools/{tool_id}/bind/{agent_id}", ("DELETE",)) in paths
    assert ("/api/v1/tools/{tool_id}/execute", ("POST",)) in paths


def test_tool_create_requires_bearer_authentication():
    response = client.post("/api/v1/tools", json={"name": "manual-test-tool"})
    assert response.status_code == 401


def test_tool_list_requires_bearer_authentication():
    response = client.get("/api/v1/tools")
    assert response.status_code == 401


def test_tool_enable_requires_bearer_authentication():
    response = client.post("/api/v1/tools/00000000-0000-0000-0000-000000000001/enable")
    assert response.status_code == 401


def test_tool_disable_requires_bearer_authentication():
    response = client.post("/api/v1/tools/00000000-0000-0000-0000-000000000001/disable")
    assert response.status_code == 401


def test_tool_bind_requires_bearer_authentication():
    response = client.post(
        "/api/v1/tools/00000000-0000-0000-0000-000000000001/bind/00000000-0000-0000-0000-000000000002"
    )
    assert response.status_code == 401


def test_tool_unbind_requires_bearer_authentication():
    response = client.delete(
        "/api/v1/tools/00000000-0000-0000-0000-000000000001/bind/00000000-0000-0000-0000-000000000002"
    )
    assert response.status_code == 401


def test_tool_execute_requires_bearer_authentication():
    response = client.post(
        "/api/v1/tools/00000000-0000-0000-0000-000000000001/execute",
        json={"agent_id": "00000000-0000-0000-0000-000000000002", "arguments": {}},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_tool_list_includes_disabled_tools():
    disabled = SimpleNamespace(id="disabled", enabled=False)
    enabled = SimpleNamespace(id="enabled", enabled=True)
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [disabled, enabled]
    db.execute.return_value = result

    response = await list_tools({"roles": ["admin"]}, db)

    assert response == [disabled, enabled]
    assert "tools.enabled" not in str(db.execute.call_args.args[0])


@pytest.mark.asyncio
async def test_user_tool_list_filters_disabled_tools():
    enabled = SimpleNamespace(id="enabled", enabled=True)
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [enabled]
    db.execute.return_value = result

    response = await list_tools({"roles": ["user"]}, db)

    assert response == [enabled]
    assert "tools.enabled" in str(db.execute.call_args.args[0])
