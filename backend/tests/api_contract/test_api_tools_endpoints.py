from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.tools.router import list_tools
from app.main import app

client = TestClient(app)


def test_tool_routes_are_registered():
    paths = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path.startswith("/api/v1/tools")
    }
    assert ("/api/v1/tools", ("POST",)) in paths and ("/api/v1/tools", ("GET",)) in paths
    assert ("/api/v1/tools/{tool_id}/enable", ("POST",)) in paths
    assert ("/api/v1/tools/{tool_id}/disable", ("POST",)) in paths
    assert ("/api/v1/tools/{tool_id}/execute", ("POST",)) in paths


def test_tool_endpoints_require_bearer_authentication():
    tool = "00000000-0000-0000-0000-000000000001"
    agent = "00000000-0000-0000-0000-000000000002"
    assert client.post("/api/v1/tools", json={"name": "manual-test-tool"}).status_code == 401
    assert client.get("/api/v1/tools").status_code == 401
    assert client.post(f"/api/v1/tools/{tool}/enable").status_code == 401
    assert client.post(f"/api/v1/tools/{tool}/disable").status_code == 401
    assert client.post(f"/api/v1/tools/{tool}/bind/{agent}").status_code == 401
    assert client.delete(f"/api/v1/tools/{tool}/bind/{agent}").status_code == 401
    assert client.post(
        f"/api/v1/tools/{tool}/execute", json={"agent_id": agent, "arguments": {}}
    ).status_code == 401


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


@pytest.mark.asyncio
async def test_user_tool_list_filters_disabled_tools():
    enabled = SimpleNamespace(id="enabled", enabled=True)
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [enabled]
    db.execute.return_value = result
    response = await list_tools({"roles": ["user"]}, db)
    assert response == [enabled]
