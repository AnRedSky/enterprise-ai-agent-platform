"""Workflow Worker 单元测试：验证独立消费器的并发编排、恢复、租约与停止语义。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services.workflow_worker import WorkflowWorker


@dataclass(frozen=True)
class _ClaimedExecution:
    """测试替身：与 WorkflowWorker.claim_one 的 Execution 契约保持一致。"""

    id: UUID


class _FakeScalarResult:
    """测试替身：提供 SQLAlchemy 结果的 scalars/all 最小契约。"""

    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return list(self._values)

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None


class _FakeRecoveryDb:
    """测试替身：只覆盖 Worker 恢复遗留 Node 所需的查询接口。"""

    def __init__(self, nodes):
        self.nodes = nodes

    async def execute(self, _statement):
        return _FakeScalarResult(self.nodes)


class _FakeRecoveryService:
    """测试替身：记录恢复阶段的 Node 状态转换。"""

    def __init__(self, nodes):
        self.db = _FakeRecoveryDb(nodes)
        self.transitions: list[tuple[str, str, str]] = []

    async def transition_node(self, _execution, node_id, target_status, **kwargs):
        self.transitions.append((node_id, target_status, kwargs["error_code"]))


class _FakeResumeDb:
    """测试替身：按查询顺序返回 Resume 来源 Execution 与 Checkpoint。"""

    def __init__(self, source, checkpoint):
        self.results = [_FakeScalarResult([source]), _FakeScalarResult([checkpoint])]

    async def execute(self, _statement):
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_dispatch_once_runs_each_claimed_execution_once() -> None:
    """一轮 dispatch 应为每个成功 claim 的 Execution 创建一个消费任务。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=3, lease_seconds=30)
    execution_ids = [uuid4(), uuid4(), uuid4()]
    claimed = [_ClaimedExecution(item) for item in execution_ids]
    executed: list[str] = []

    async def fake_claim_one():
        return claimed.pop(0) if claimed else None

    async def fake_run(execution_id):
        executed.append(str(execution_id))

    worker.claim_one = fake_claim_one  # type: ignore[method-assign]
    worker._run_with_guard = fake_run  # type: ignore[method-assign]

    count = await worker.dispatch_once()

    assert count == 3
    assert set(executed) == {str(item) for item in execution_ids}
    assert len(executed) == 3


@pytest.mark.asyncio
async def test_run_forever_stops_without_restarting_after_stop() -> None:
    """stop 后 Worker 不应继续轮询。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=30)
    calls = 0

    async def fake_dispatch_once():
        nonlocal calls
        calls += 1
        worker.stop()
        return 0

    worker.dispatch_once = fake_dispatch_once  # type: ignore[method-assign]

    await asyncio.wait_for(worker.run_forever(), timeout=1)

    assert calls == 1
    assert worker._stop_event.is_set()


@pytest.mark.asyncio
async def test_recover_orphaned_running_nodes_before_runtime_retry() -> None:
    """pending Execution 上遗留的 running Node 必须先转 failed，不能直接触发 running → running。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=30)
    execution = _ClaimedExecution(uuid4())
    nodes = [
        type("Node", (), {"node_id": "agent-1"})(),
        type("Node", (), {"node_id": "agent-2"})(),
    ]
    service = _FakeRecoveryService(nodes)

    recovered = await worker._recover_orphaned_running_nodes(execution, service)  # type: ignore[arg-type]

    assert recovered == 2
    assert service.transitions == [
        ("agent-1", "failed", "WORKER_RECOVERY_INTERRUPTED"),
        ("agent-2", "failed", "WORKER_RECOVERY_INTERRUPTED"),
    ]


@pytest.mark.asyncio
async def test_recover_orphaned_running_nodes_is_noop_when_state_is_consistent() -> None:
    """没有遗留 running Node 时恢复阶段不得产生任何状态变更。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=30)
    execution = _ClaimedExecution(uuid4())
    service = _FakeRecoveryService([])

    recovered = await worker._recover_orphaned_running_nodes(execution, service)  # type: ignore[arg-type]

    assert recovered == 0
    assert service.transitions == []


@pytest.mark.asyncio
async def test_prepare_resume_runtime_preserves_full_dag_definition() -> None:
    """Resume Worker 只能恢复 Checkpoint 状态，不得提前裁剪 DAG Definition。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=30)
    source_id = uuid4()
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        resume_of_execution_id=source_id,
        resume_checkpoint_sequence=0,
        input_data={"stale": True},
    )
    source = SimpleNamespace(
        id=source_id,
        status="failed",
        worker_owner=None,
        workflow_version_id=uuid4(),
    )
    execution.workflow_version_id = source.workflow_version_id
    checkpoint = SimpleNamespace(
        checkpoint_reason="node.completed",
        node_status="completed",
        execution_status="running",
        node_id="prepare",
        state_data={"source": "resume"},
    )
    definition = {
        "config": {"timeout_ms": 5000},
        "nodes": [
            {"id": "prepare", "type": "input", "config": {}},
            {"id": "provider-call", "type": "agent", "config": {"agent_id": "agent-1"}},
        ],
        "edges": [{"source": "prepare", "target": "provider-call"}],
    }
    version = SimpleNamespace(id=execution.workflow_version_id, status="published", definition=definition)

    updated_execution, runtime_version = await worker._prepare_resume_runtime(
        _FakeResumeDb(source, checkpoint), execution, version  # type: ignore[arg-type]
    )

    assert updated_execution.input_data == checkpoint.state_data
    assert runtime_version is version
    assert runtime_version.definition == definition
    assert [node["id"] for node in runtime_version.definition["nodes"]] == ["prepare", "provider-call"]


@pytest.mark.asyncio
async def test_renew_lease_forever_retries_transient_failure_then_exits_on_lost_ownership(monkeypatch) -> None:
    """Heartbeat 的瞬态失败必须继续重试，ownership 失效后立即退出且不再等待下一轮。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=30)
    calls = 0
    sleeps = 0

    async def fake_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1

    async def fake_renew(_execution_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("temporary database interruption")
        return False

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    worker._renew_lease_once = fake_renew  # type: ignore[method-assign]

    await worker._renew_lease_forever(uuid4())

    assert calls == 2
    # 第一次是瞬态异常后的下一轮等待；第二次 renew 已明确失去 ownership，必须立即退出。
    assert sleeps == 1


def test_worker_rejects_invalid_runtime_parameters() -> None:
    """Worker 基础并发与租约参数必须在构造阶段拒绝非法值。"""
    with pytest.raises(ValueError):
        WorkflowWorker(concurrency=0)
    with pytest.raises(ValueError):
        WorkflowWorker(lease_seconds=0)
    with pytest.raises(ValueError):
        WorkflowWorker(poll_interval_seconds=0)
