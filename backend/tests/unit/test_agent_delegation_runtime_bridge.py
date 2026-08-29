"""B2 Delegation Runtime Bridge 单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

from app.services.agent_delegation.runtime_bridge import AgentDelegationRuntimeBridge, DelegationRuntimeContext
from app.services.workflow_worker.resume_runtime import DurableResumeWorkflowRuntime


def _context():
    return DelegationRuntimeContext(
        delegation_id=uuid4(),
        target_agent_version_id=uuid4(),
        target_agent_id=uuid4(),
        model_profile_id=uuid4(),
        input_data={"prompt": "target"},
        selected_context_refs=("input:task",),
        allowed_tools=("tool:read",),
        trace_id=str(uuid4()),
        prompt="target",
        timeout_at=None,
    )


def _parent():
    return SimpleNamespace(
        id=uuid4(), workflow_id=uuid4(), version=1,
        definition={
            "config": {"timeout_ms": 30000},
            "nodes": [{"id": "parent", "type": "agent", "config": {"agent_id": str(uuid4()), "prompt": "parent"}}],
            "edges": [],
        },
        status="published", created_by=uuid4(),
    )


def test_delegation_runtime_bridge_builds_isolated_target_version():
    """桥接必须只创建内存目标 Node，不修改父 Workflow Definition。"""
    parent = _parent()
    parent_definition = parent.definition
    context = _context()

    runtime_version = AgentDelegationRuntimeBridge.build_runtime_version(parent, context)

    assert runtime_version.workflow_id == parent.workflow_id
    assert runtime_version.definition["nodes"][0]["config"]["agent_id"] == str(context.target_agent_id)
    assert runtime_version.definition["nodes"][0]["config"]["prompt"] == "target"
    assert runtime_version.definition["config"]["delegation_context"]["target_agent_version_id"] == str(context.target_agent_version_id)
    assert runtime_version.definition["config"]["delegation_context"]["model_profile_id"] == str(context.model_profile_id)
    assert runtime_version.definition["config"]["delegation_context"]["selected_context_refs"] == ["input:task"]
    assert runtime_version.definition["config"]["delegation_context"]["allowed_tools"] == ["tool:read"]
    assert "edges" not in runtime_version.definition
    assert parent.definition == parent_definition


def test_delegation_runtime_bridge_output_passes_worker_definition_validation():
    """单 Node Delegation Runtime 必须由 Worker Runtime 接受，且不能伪造 DAG edge。"""
    runtime_version = AgentDelegationRuntimeBridge.build_runtime_version(_parent(), _context())

    nodes = DurableResumeWorkflowRuntime.validate_definition(runtime_version.definition)

    assert [node["id"] for node in nodes] == ["delegation.target"]
    assert "edges" not in runtime_version.definition


def test_delegation_runtime_bridge_resolves_structured_input_without_parent_state():
    """缺少 prompt 时只根据 Delegation 自身显式输入构造确定性 prompt。"""
    assert AgentDelegationRuntimeBridge._resolve_prompt({"task": "hello", "value": 1}) == '{"task": "hello", "value": 1}'
