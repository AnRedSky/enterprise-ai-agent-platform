from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.runtime.workflow.dag_runtime import WorkflowRuntime
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlan
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlanner


@pytest.mark.asyncio
async def test_initial_multi_root_dag_creates_independent_branch_states_from_input():
    """验证首次执行存在多个 root 时，每个 frontier 都获得独立输入快照。"""
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [])
    )
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), resume_of_execution_id=None)
    definition = {
        "nodes": [
            {"id": "left", "type": "input", "config": {}},
            {"id": "right", "type": "input", "config": {}},
            {"id": "join", "type": "join", "config": {}},
        ],
        "edges": [
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
        ],
    }
    input_data = {"request_id": "r-1", "content": "hello"}

    plan, branch_state_data = await runtime._resolve_dag_context(execution, definition, input_data)

    assert plan.frontier_node_ids == ("left", "right")
    assert branch_state_data == {"left": input_data, "right": input_data}
    assert branch_state_data["left"] is not branch_state_data["right"]
    assert plan.selected_predecessor_node_ids == ()


def test_dag_runtime_join_node_is_registered_without_reimplementing_base_runtime():
    """验证 Join 只扩展 Node 类型，不复制基础 Runtime 的执行能力。"""
    assert "join" in WorkflowRuntime.NODE_TYPES
    assert "agent" in WorkflowRuntime.NODE_TYPES
    assert WorkflowRuntime.execute_node.__qualname__.startswith("WorkflowRuntime.execute_node")


@pytest.mark.asyncio
async def test_completed_resume_node_query_is_tenant_scoped():
    """验证 Durable Resume 读取 Node 完成事实时强制使用当前租户边界。"""
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), resume_of_execution_id=uuid4())

    await runtime._load_completed_resume_nodes(execution)

    query = db.execute.call_args.args[0]
    sql = str(query)
    assert "workflow_executions.tenant_id" in sql
    assert "workflow_node_executions.execution_id IN" in sql
    assert "workflow_node_executions.status" in sql


@pytest.mark.asyncio
async def test_completed_resume_node_query_keeps_source_and_current_execution_scope():
    """验证 Resume 查询同时限定 Source/Current Execution，不扩大读取范围。"""
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), resume_of_execution_id=uuid4())

    await runtime._load_completed_resume_nodes(execution)

    query = db.execute.call_args.args[0]
    compiled = query.compile().params
    execution_ids = next(value for key, value in compiled.items() if key.startswith("execution_id"))
    assert set(execution_ids) == {execution.id, execution.resume_of_execution_id}


def test_runtime_planner_reuses_supplied_resume_plan_without_replanning():
    """验证 Runtime 只能消费已经计算出的 Planner 结果，不在同一次 resolution 中二次计算 Decision。"""
    definition = {
        "nodes": [
            {"id": "a", "type": "input", "config": {}},
            {"id": "b", "type": "input", "config": {}},
        ],
        "edges": [{"source": "a", "target": "b"}],
    }
    resume_plan = WorkflowDagResumePlan(
        completed_node_ids=("a",),
        frontier_node_ids=("b",),
        selected_predecessor_node_ids=(("b", ("a",)),),
        decision_fingerprint="fingerprint-1",
    )

    with patch(
        "app.services.workflow.checkpoint.recovery.dag_runtime.WorkflowDagResumePlanner.plan",
        side_effect=AssertionError("Runtime planner must not recalculate the supplied Decision"),
    ):
        runtime_plan = WorkflowDagResumeRuntimePlanner.plan(
            definition=definition,
            completed_node_ids={"a"},
            state_data={"request_id": "r-1"},
            resume_plan=resume_plan,
        )

    assert runtime_plan.completed_node_ids == ("a",)
    assert runtime_plan.frontier_node_ids == ("b",)
    assert runtime_plan.selected_predecessor_node_ids == (("b", ("a",)),)
    assert runtime_plan.decision_fingerprint == "fingerprint-1"
