from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.runtime.workflow import WorkflowRuntime


def test_workflow_runtime_accepts_only_supported_sequential_nodes():
    nodes = WorkflowRuntime.validate_definition({
        "nodes": [
            {"id": "input", "type": "input"},
            {"id": "agent", "type": "agent", "config": {"agent_id": str(uuid4())}},
            {"id": "output", "type": "output"},
        ]
    })
    assert [node["type"] for node in nodes] == ["input", "agent", "output"]


@pytest.mark.parametrize("definition", [{}, {"nodes": []}, {"nodes": [{"id": "a", "type": "unknown"}]}])
def test_workflow_runtime_rejects_invalid_definition(definition):
    with pytest.raises(HTTPException) as exc:
        WorkflowRuntime.validate_definition(definition)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_input_and_output_nodes_preserve_payload():
    runtime = WorkflowRuntime(AsyncMock())
    actor = uuid4()
    session = uuid4()
    payload = {"input": "hello", "value": 1}
    assert await runtime.execute_node({"id": "i", "type": "input", "config": {}}, payload, actor, False, session) == payload
    assert await runtime.execute_node({"id": "o", "type": "output", "config": {}}, payload, actor, False, session) == payload


@pytest.mark.asyncio
async def test_agent_node_uses_published_agent_version_and_governed_gateway():
    db = AsyncMock()
    agent_id = uuid4()
    owner_id = uuid4()
    tenant_id = uuid4()
    organization_id = uuid4()
    version_id = uuid4()
    profile_id = uuid4()
    agent = SimpleNamespace(id=agent_id, owner_id=owner_id, status="published", published_version_id=version_id)
    version = SimpleNamespace(id=version_id, agent_id=agent_id, system_prompt="system", model_id="legacy-model-id", model_profile_id=profile_id, version="1.0.0")
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalar_one_or_none=lambda: agent),
        SimpleNamespace(scalar_one_or_none=lambda: version),
        SimpleNamespace(scalar_one_or_none=lambda: organization_id),
    ])
    runtime = WorkflowRuntime(db)
    runtime.governance.invoke = AsyncMock(return_value=SimpleNamespace(content="ok", usage=None, model="governed-model"))
    result = await runtime.execute_node({"id": "agent", "type": "agent", "config": {"agent_id": str(agent_id)}}, {"input": "hello"}, owner_id, False, uuid4(), tenant_id)
    assert result["content"] == "ok"
    assert result["model_id"] == "governed-model"
    runtime.governance.invoke.assert_awaited_once()
    request = runtime.governance.invoke.call_args.args[0]
    assert request.organization_id == organization_id
    assert request.routing_strategy == "explicit_profile"
    assert request.profile_id == profile_id


@pytest.mark.asyncio
async def test_agent_node_without_profile_uses_organization_default_routing():
    db = AsyncMock()
    agent_id = uuid4()
    owner_id = uuid4()
    tenant_id = uuid4()
    organization_id = uuid4()
    version_id = uuid4()
    agent = SimpleNamespace(id=agent_id, owner_id=owner_id, status="published", published_version_id=version_id)
    version = SimpleNamespace(id=version_id, agent_id=agent_id, system_prompt="system", model_id="legacy-model-id", model_profile_id=None, version="1.0.0")
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalar_one_or_none=lambda: agent),
        SimpleNamespace(scalar_one_or_none=lambda: version),
        SimpleNamespace(scalar_one_or_none=lambda: organization_id),
    ])
    runtime = WorkflowRuntime(db)
    runtime.governance.invoke = AsyncMock(return_value=SimpleNamespace(content="ok", usage=None, model="default-model"))
    result = await runtime.execute_node({"id": "agent", "type": "agent", "config": {"agent_id": str(agent_id)}}, {"input": "hello"}, owner_id, False, uuid4(), tenant_id)
    assert result["content"] == "ok"
    request = runtime.governance.invoke.call_args.args[0]
    assert request.routing_strategy == "organization_default"
    assert request.profile_id is None


@pytest.mark.asyncio
async def test_agent_node_query_is_scoped_to_workflow_tenant():
    db = AsyncMock()
    agent_id = uuid4()
    owner_id = uuid4()
    tenant_id = uuid4()
    organization_id = uuid4()
    version_id = uuid4()
    profile_id = uuid4()
    agent = SimpleNamespace(id=agent_id, owner_id=owner_id, status="published", published_version_id=version_id)
    version = SimpleNamespace(id=version_id, agent_id=agent_id, system_prompt="system", model_id="legacy-model-id", model_profile_id=profile_id, version="1.0.0")
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalar_one_or_none=lambda: agent),
        SimpleNamespace(scalar_one_or_none=lambda: version),
        SimpleNamespace(scalar_one_or_none=lambda: organization_id),
    ])
    runtime = WorkflowRuntime(db)
    runtime.governance.invoke = AsyncMock(return_value=SimpleNamespace(content="ok", usage=None, model="governed-model"))
    result = await runtime.execute_node({"id": "agent", "type": "agent", "config": {"agent_id": str(agent_id)}}, {"input": "hello"}, owner_id, True, uuid4(), tenant_id)
    assert result["content"] == "ok"
    assert result["model_id"] == "governed-model"
    agent_query = db.execute.call_args_list[0].args[0]
    assert "users" in str(agent_query)
    assert "tenant_id" in str(agent_query)


def test_resume_runtime_builds_independent_branch_states_from_completed_predecessors():
    definition = {
        "nodes": [
            {"id": "root", "type": "input"},
            {"id": "left", "type": "input"},
            {"id": "right", "type": "input"},
            {"id": "join", "type": "output"},
        ],
        "edges": [
            {"source": "root", "target": "left"},
            {"source": "root", "target": "right"},
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
        ],
    }
    root = SimpleNamespace(node_id="root", output_data={"root": 1})
    states = WorkflowRuntime._build_frontier_branch_states(definition, ("left", "right"), [root])
    assert states == {"left": {"root": 1}, "right": {"root": 1}}


def test_conditional_join_branch_state_uses_only_selected_predecessors():
    definition = {
        "nodes": [
            {"id": "root", "type": "input"},
            {"id": "approved", "type": "input"},
            {"id": "rejected", "type": "input"},
            {"id": "join", "type": "output"},
        ],
        "edges": [
            {"source": "root", "target": "approved", "condition": {"op": "eq", "path": "status", "value": "approved"}},
            {"source": "root", "target": "rejected", "condition": {"op": "eq", "path": "status", "value": "rejected"}},
            {"source": "approved", "target": "join"},
            {"source": "rejected", "target": "join"},
        ],
    }
    nodes = [SimpleNamespace(node_id="approved", output_data={"approved": 1})]
    states = WorkflowRuntime._build_frontier_branch_states(definition, ("join",), nodes, (("join", ("approved",)),))
    assert states == {"join": {"approved": 1}}


@pytest.mark.asyncio
async def test_initial_dag_context_starts_from_root_and_uses_same_planner_contract():
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    runtime = WorkflowRuntime(db)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), resume_of_execution_id=None)
    definition = {
        "nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "approved", "type": "input", "config": {}},
            {"id": "fallback", "type": "input", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "approved", "condition": {"op": "eq", "path": "status", "value": "approved"}},
            {"source": "input", "target": "fallback", "default": True},
        ],
    }
    plan, branch_state_data = await runtime._resolve_dag_context(execution, definition, {"status": "approved"})
    assert plan.frontier_node_ids == ("input",)
    assert branch_state_data == {}


def test_resume_runtime_merges_join_predecessor_states_without_overwrite():
    definition = {
        "nodes": [
            {"id": "root", "type": "input"},
            {"id": "left", "type": "input"},
            {"id": "right", "type": "input"},
            {"id": "join", "type": "output"},
        ],
        "edges": [
            {"source": "root", "target": "left"},
            {"source": "root", "target": "right"},
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
        ],
    }
    nodes = [
        SimpleNamespace(node_id="left", output_data={"left": 1}),
        SimpleNamespace(node_id="right", output_data={"right": 2}),
    ]
    states = WorkflowRuntime._build_frontier_branch_states(definition, ("join",), nodes)
    assert states == {"join": {"left": 1, "right": 2}}
