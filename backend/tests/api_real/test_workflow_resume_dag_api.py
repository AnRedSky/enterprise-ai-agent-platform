"""Durable Resume DAG Runtime 真实 HTTP 验收测试扩展。

职责：在既有真实 Resume acceptance 基础上验证三节点线性 DAG 的完整 Definition 不被 Worker 裁剪，恢复后从单一 frontier 连续执行到尾节点，并覆盖 frontier 成功后后续节点再次失败的边界。
边界：只使用真实 HTTP、真实 PostgreSQL 与人工启动的独立 Worker；不启动、停止或重启服务。
关键依赖：既有 Resume Real API 测试辅助函数、Durable Resume Contract、PostgreSQL Checkpoint 与独立 Worker。
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeContractService
from tests.api_real.test_workflow_resume_api import _client, _resume_fixture_server, _require_context

pytestmark = pytest.mark.real_api


async def _wait_for_status(execution_id: str, expected: str, timeout_seconds: float = 30.0) -> WorkflowExecution:
    """等待独立 Worker 将真实 Execution 推进到指定终态。

    Args:
        execution_id: 待观察的 Execution ID。
        expected: 期望的持久化状态。
        timeout_seconds: 最大等待秒数。

    Returns:
        达到期望状态的 WorkflowExecution。

    Raises:
        AssertionError: 在超时时间内未达到期望状态。
    """
    from time import monotonic

    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        async with SessionLocal() as db:
            execution = (
                await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
            ).scalar_one_or_none()
            if execution is not None and execution.status == expected:
                return execution
        await asyncio.sleep(0.2)
    raise AssertionError(f"Execution did not reach {expected}: {execution_id}")


async def _resume(source_id: str) -> WorkflowExecution:
    """通过正式 Resume Contract 创建 Resume，并在同一事务内完成 Durable Bootstrap。"""
    async with SessionLocal() as db:
        source = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == source_id))
        ).scalar_one()
        outcome = await WorkflowExecutionResumeContractService(db).resume_with_outcome(source, source.created_by)
        return outcome.execution


@pytest.mark.asyncio
async def test_real_worker_executes_full_linear_dag_after_resume():
    """验证 Source 在中间 Node 失败后，Resume 使用完整三节点 DAG 执行 frontier 及其后续节点。"""
    _require_context()

    suffix = uuid.uuid4().hex[:10]
    provider_id = None
    profile_id = None

    with _resume_fixture_server() as fixture:
        endpoint, state, lock = fixture
        try:
            with _client() as client:
                provider = client.post(
                    "/model-providers",
                    json={
                        "organization_id": os.environ["ORGANIZATION_ID"],
                        "name": f"durable-resume-dag-provider-{suffix}",
                        "provider_type": "openai-compatible",
                        "provider_name": f"durable-resume-dag-provider-{suffix}",
                        "endpoint": endpoint,
                        "credential_ref": f"DURABLE_RESUME_DAG_SECRET_{suffix}",
                    },
                )
                assert provider.status_code == 201, provider.text
                provider_id = provider.json()["id"]
                profile = client.post(
                    f"/model-providers/{provider_id}/profiles",
                    json={
                        "name": f"durable-resume-dag-profile-{suffix}",
                        "model_type": "chat",
                        "model_name": "resume-fixture-model",
                        "is_default": True,
                    },
                )
                assert profile.status_code == 201, profile.text
                profile_id = profile.json()["id"]
                agent = client.post(
                    "/agents",
                    json={
                        "name": f"Durable Resume DAG Agent {suffix}",
                        "description": "Real Worker full DAG resume acceptance fixture",
                        "system_prompt": "Return the provider result without modification.",
                        "model_id": f"durable-resume-dag-model-{suffix}",
                        "model_profile_id": profile_id,
                    },
                )
                assert agent.status_code == 200, agent.text
                agent_id = agent.json()["id"]
                versions = client.get(f"/agents/{agent_id}/versions")
                assert versions.status_code == 200, versions.text
                published_agent = client.post(
                    f"/agents/{agent_id}/publish",
                    json={"version_id": versions.json()[0]["id"]},
                )
                assert published_agent.status_code == 200, published_agent.text

                workflow = client.post(
                    "/workflows",
                    json={
                        "name": f"Durable Resume Full DAG {suffix}",
                        "description": "Three-node DAG resume acceptance",
                    },
                )
                assert workflow.status_code == 201, workflow.text
                workflow_id = workflow.json()["id"]
                version = client.post(
                    f"/workflows/{workflow_id}/versions",
                    json={
                        "definition": {
                            "config": {"timeout_ms": 5000, "retry_budget": {"max_retries": 0}},
                            "nodes": [
                                {"id": "prepare", "type": "input", "config": {}},
                                {
                                    "id": "provider-call",
                                    "type": "agent",
                                    "config": {
                                        "agent_id": agent_id,
                                        "prompt": "durable full DAG resume acceptance",
                                        "retry": {
                                            "max_attempts": 1,
                                            "backoff_ms": 0,
                                            "max_backoff_ms": 0,
                                            "jitter_ms": 0,
                                            "retryable_error_codes": ["HTTP_503"],
                                        },
                                    },
                                },
                                {"id": "finish", "type": "output", "config": {}},
                            ],
                            "edges": [
                                {"source": "prepare", "target": "provider-call"},
                                {"source": "provider-call", "target": "finish"},
                            ],
                        }
                    },
                )
                assert version.status_code == 201, version.text
                version_id = version.json()["id"]
                published_workflow = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
                assert published_workflow.status_code == 200, published_workflow.text
                execution = client.post(
                    f"/workflows/{workflow_id}/executions",
                    json={"input_data": {"source": "full-dag-resume"}},
                )
                assert execution.status_code == 201, execution.text
                source_id = execution.json()["id"]
                run = client.post(f"/workflows/executions/{source_id}/run")
                assert run.status_code in (409, 503), run.text

            source = await _wait_for_status(source_id, "failed")
            async with SessionLocal() as db:
                source_nodes = (
                    await db.execute(
                        select(WorkflowNodeExecution)
                        .where(WorkflowNodeExecution.execution_id == source.id)
                        .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
                    )
                ).scalars().all()
                checkpoints = (
                    await db.execute(
                        select(WorkflowExecutionCheckpoint)
                        .where(WorkflowExecutionCheckpoint.execution_id == source.id)
                        .order_by(WorkflowExecutionCheckpoint.sequence.asc())
                    )
                ).scalars().all()

            assert [(node.node_id, node.status) for node in source_nodes] == [
                ("prepare", "completed"),
                ("provider-call", "failed"),
            ]
            assert len(checkpoints) == 1
            assert checkpoints[0].node_id == "prepare"

            resume = await _resume(source_id)
            resumed = await _wait_for_status(str(resume.id), "completed")
            assert resumed.status == "completed"
            assert resumed.workflow_version_id == source.workflow_version_id
            assert resumed.resume_of_execution_id == source.id
            assert resumed.resume_checkpoint_sequence == checkpoints[0].sequence
            assert resumed.worker_owner is None

            async with SessionLocal() as db:
                resume_nodes = (
                    await db.execute(
                        select(WorkflowNodeExecution)
                        .where(WorkflowNodeExecution.execution_id == resume.id)
                        .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
                    )
                ).scalars().all()
                resume_checkpoints = (
                    await db.execute(
                        select(WorkflowExecutionCheckpoint)
                        .where(WorkflowExecutionCheckpoint.execution_id == resume.id)
                        .order_by(WorkflowExecutionCheckpoint.sequence.asc())
                    )
                ).scalars().all()

            assert [(node.node_id, node.status) for node in resume_nodes] == [
                ("prepare", "completed"),
                ("provider-call", "completed"),
                ("finish", "completed"),
            ]
            assert [checkpoint.node_id for checkpoint in resume_checkpoints] == ["provider-call", "finish"]
            assert [checkpoint.sequence for checkpoint in resume_checkpoints] == [0, 1]
            with lock:
                assert state["calls"] == 2
        finally:
            if profile_id or provider_id:
                with _client() as cleanup:
                    if profile_id:
                        response = cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                        assert response.status_code == 204, response.text
                    if provider_id:
                        response = cleanup.delete(f"/model-providers/{provider_id}")
                        assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_real_worker_resume_dag_failure_after_frontier_preserves_checkpoint_and_lease():
    """验证 Resume frontier 成功后后续 Node 再次失败时，Resume Checkpoint、lineage 与 Worker ownership 仍保持一致。"""
    _require_context()

    suffix = uuid.uuid4().hex[:10]
    broken_agent_id = str(uuid.uuid4())
    provider_id = None
    profile_id = None

    with _resume_fixture_server() as fixture:
        endpoint, state, lock = fixture
        try:
            with _client() as client:
                provider = client.post(
                    "/model-providers",
                    json={
                        "organization_id": os.environ["ORGANIZATION_ID"],
                        "name": f"durable-resume-dag-failure-provider-{suffix}",
                        "provider_type": "openai-compatible",
                        "provider_name": f"durable-resume-dag-failure-provider-{suffix}",
                        "endpoint": endpoint,
                        "credential_ref": f"DURABLE_RESUME_DAG_FAILURE_SECRET_{suffix}",
                    },
                )
                assert provider.status_code == 201, provider.text
                provider_id = provider.json()["id"]
                profile = client.post(
                    f"/model-providers/{provider_id}/profiles",
                    json={
                        "name": f"durable-resume-dag-failure-profile-{suffix}",
                        "model_type": "chat",
                        "model_name": "resume-fixture-model",
                        "is_default": True,
                    },
                )
                assert profile.status_code == 201, profile.text
                profile_id = profile.json()["id"]
                agent = client.post(
                    "/agents",
                    json={
                        "name": f"Durable Resume DAG Failure Agent {suffix}",
                        "description": "Real Worker DAG resume failure fixture",
                        "system_prompt": "Return the provider result without modification.",
                        "model_id": f"durable-resume-dag-failure-model-{suffix}",
                        "model_profile_id": profile_id,
                    },
                )
                assert agent.status_code == 200, agent.text
                agent_id = agent.json()["id"]
                versions = client.get(f"/agents/{agent_id}/versions")
                assert versions.status_code == 200, versions.text
                published_agent = client.post(
                    f"/agents/{agent_id}/publish",
                    json={"version_id": versions.json()[0]["id"]},
                )
                assert published_agent.status_code == 200, published_agent.text

                workflow = client.post(
                    "/workflows",
                    json={
                        "name": f"Durable Resume DAG Failure {suffix}",
                        "description": "Resume frontier success followed by downstream failure",
                    },
                )
                assert workflow.status_code == 201, workflow.text
                workflow_id = workflow.json()["id"]
                version = client.post(
                    f"/workflows/{workflow_id}/versions",
                    json={
                        "definition": {
                            "config": {"timeout_ms": 5000, "retry_budget": {"max_retries": 0}},
                            "nodes": [
                                {"id": "prepare", "type": "input", "config": {}},
                                {
                                    "id": "provider-call",
                                    "type": "agent",
                                    "config": {
                                        "agent_id": agent_id,
                                        "prompt": "durable DAG resume failure boundary",
                                        "retry": {
                                            "max_attempts": 1,
                                            "backoff_ms": 0,
                                            "max_backoff_ms": 0,
                                            "jitter_ms": 0,
                                            "retryable_error_codes": ["HTTP_503"],
                                        },
                                    },
                                },
                                {
                                    "id": "broken-after-resume",
                                    "type": "agent",
                                    "config": {
                                        "agent_id": broken_agent_id,
                                        "prompt": "must fail after resumed frontier succeeds",
                                        "retry": {
                                            "max_attempts": 1,
                                            "backoff_ms": 0,
                                            "max_backoff_ms": 0,
                                            "jitter_ms": 0,
                                            "retryable_error_codes": [],
                                        },
                                    },
                                },
                            ],
                            "edges": [
                                {"source": "prepare", "target": "provider-call"},
                                {"source": "provider-call", "target": "broken-after-resume"},
                            ],
                        }
                    },
                )
                assert version.status_code == 201, version.text
                version_id = version.json()["id"]
                published_workflow = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
                assert published_workflow.status_code == 200, published_workflow.text
                execution = client.post(
                    f"/workflows/{workflow_id}/executions",
                    json={"input_data": {"source": "full-dag-resume-failure"}},
                )
                assert execution.status_code == 201, execution.text
                source_id = execution.json()["id"]
                run = client.post(f"/workflows/executions/{source_id}/run")
                assert run.status_code in (409, 503), run.text

            source = await _wait_for_status(source_id, "failed")
            assert source.worker_owner is None
            assert source.workflow_version_id == uuid.UUID(version_id)

            async with SessionLocal() as db:
                source_checkpoints = (
                    await db.execute(
                        select(WorkflowExecutionCheckpoint)
                        .where(WorkflowExecutionCheckpoint.execution_id == source.id)
                        .order_by(WorkflowExecutionCheckpoint.sequence.asc())
                    )
                ).scalars().all()
                source_nodes = (
                    await db.execute(
                        select(WorkflowNodeExecution)
                        .where(WorkflowNodeExecution.execution_id == source.id)
                        .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
                    )
                ).scalars().all()

            assert [(node.node_id, node.status) for node in source_nodes] == [
                ("prepare", "completed"),
                ("provider-call", "failed"),
            ]
            assert [(checkpoint.sequence, checkpoint.node_id, checkpoint.node_status) for checkpoint in source_checkpoints] == [
                (0, "prepare", "completed"),
            ]

            resume = await _resume(source_id)
            resumed = await _wait_for_status(str(resume.id), "failed")
            assert resumed.status == "failed"
            assert resumed.worker_owner is None
            assert resumed.workflow_version_id == source.workflow_version_id
            assert resumed.resume_of_execution_id == source.id
            assert resumed.resume_checkpoint_sequence == source_checkpoints[0].sequence

            async with SessionLocal() as db:
                resume_nodes = (
                    await db.execute(
                        select(WorkflowNodeExecution)
                        .where(WorkflowNodeExecution.execution_id == resume.id)
                        .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
                    )
                ).scalars().all()
                resume_checkpoints = (
                    await db.execute(
                        select(WorkflowExecutionCheckpoint)
                        .where(WorkflowExecutionCheckpoint.execution_id == resume.id)
                        .order_by(WorkflowExecutionCheckpoint.sequence.asc())
                    )
                ).scalars().all()
                source_after = (
                    await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == source.id))
                ).scalar_one()

            assert [(node.node_id, node.status) for node in resume_nodes] == [
                ("prepare", "completed"),
                ("provider-call", "completed"),
                ("broken-after-resume", "failed"),
            ]
            assert [(checkpoint.sequence, checkpoint.node_id, checkpoint.node_status) for checkpoint in resume_checkpoints] == [
                (0, "provider-call", "completed"),
            ]
            assert source_after.status == "failed"
            assert source_after.worker_owner is None
            with lock:
                assert state["calls"] == 2
        finally:
            if profile_id or provider_id:
                with _client() as cleanup:
                    if profile_id:
                        response = cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                        assert response.status_code == 204, response.text
                    if provider_id:
                        response = cleanup.delete(f"/model-providers/{provider_id}")
                        assert response.status_code == 204, response.text
