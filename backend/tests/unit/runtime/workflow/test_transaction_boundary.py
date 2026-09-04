"""Workflow Runtime 单元测试：验证上层事务提交边界能够传递到终态转换。

职责：锁定 WorkflowRuntime.execute(commit=False) 不得在 Execution terminal transition 中提前提交。
边界：不访问 PostgreSQL，不启动 API、Worker、Scheduler 或 Redis，不执行真实模型 Provider。
关键依赖：WorkflowRuntime 与可控的 WorkflowExecutionService 替身。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.runtime.workflow import WorkflowRuntime


@pytest.mark.asyncio
async def test_runtime_execute_forwards_commit_boundary_to_terminal_transition(monkeypatch) -> None:
    """验证 commit=False 时 Runtime 的最终 Execution 状态转换不会提前提交事务。"""
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status="pending",
        input_data={"source": "operator"},
    )
    version = SimpleNamespace(
        definition={
            "config": {},
            "nodes": [{"id": "input", "type": "input", "config": {}}],
            "edges": [],
        }
    )
    transition = AsyncMock()
    service = SimpleNamespace(transition=transition)
    runtime = WorkflowRuntime(SimpleNamespace(), execution_service=service)

    monkeypatch.setattr(
        WorkflowRuntime,
        "validate_definition",
        classmethod(lambda cls, definition, **kwargs: definition["nodes"]),
    )
    monkeypatch.setattr(
        runtime,
        "_execute_node_with_policy",
        AsyncMock(return_value={"source": "operator"}),
    )

    result = await runtime.execute(execution, version, uuid4(), commit=False)

    assert result == {"source": "operator"}
    transition.assert_awaited_once()
    assert transition.await_args.kwargs["commit"] is False
