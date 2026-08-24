"""Tool Runtime 服务单元测试。

职责：验证 Tool 绑定、启用状态、权限与调用次数上限。
边界：不测试 HTTP 技术执行实现。
"""

from types import SimpleNamespace

import pytest

from app.services.tool import ToolExecutionContext, ToolRuntimeService
from app.tools.exceptions import ToolExecutionError


class Repo:
    def __init__(self, tool=None, binding=None):
        self.tool = tool
        self.binding = binding

    async def get(self, _):
        return self.tool

    async def get_binding(self, *_):
        return self.binding


class Permissions:
    def __init__(self, allowed):
        self.allowed = allowed

    async def __call__(self, *_):
        return self.allowed


@pytest.mark.asyncio
async def test_unbound_tool_is_rejected():
    tool = SimpleNamespace(is_active=True, input_schema={"type": "object"}, type="http")
    service = ToolRuntimeService(Repo(tool, None), Repo(), Permissions(True))
    with pytest.raises(ToolExecutionError, match="not enabled"):
        await service.execute(ToolExecutionContext(1, 2, 3), {})


@pytest.mark.asyncio
async def test_disabled_tool_is_rejected():
    tool = SimpleNamespace(is_active=False, input_schema={"type": "object"}, type="http")
    binding = SimpleNamespace(is_active=True)
    service = ToolRuntimeService(Repo(tool), Repo(binding=binding), Permissions(True))
    with pytest.raises(ToolExecutionError, match="disabled"):
        await service.execute(ToolExecutionContext(1, 2, 3), {})


@pytest.mark.asyncio
async def test_permission_is_checked_before_execution():
    tool = SimpleNamespace(is_active=True, input_schema={"type": "object"}, type="http")
    binding = SimpleNamespace(is_active=True)
    service = ToolRuntimeService(Repo(tool), Repo(binding=binding), Permissions(False))
    with pytest.raises(ToolExecutionError, match="permission"):
        await service.execute(ToolExecutionContext(1, 2, 3), {})


@pytest.mark.asyncio
async def test_execution_limit():
    service = ToolRuntimeService(Repo(), Repo(), Permissions(True), max_calls=2)
    with pytest.raises(ToolExecutionError, match="limit"):
        await service.execute(ToolExecutionContext(1, 2, 3), {}, call_count=2)
