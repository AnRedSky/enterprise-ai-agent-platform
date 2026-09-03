"""Agent Delegation B5 Audit / Trace 闭环 Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 验证 Delegation 生命周期的关键状态变化均形成
AuditLog 与 WorkflowTraceEvent，并验证 trace_id、父 Execution 与 Delegation 身份一致。
边界：不复制 Delegation 生命周期实现；只读取真实持久化结果进行闭环断言。
关键依赖：Agent Delegation API、AuditLog、WorkflowTraceEvent、PostgreSQL。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.infrastructure.db.session import SessionLocal
from app.models.core import AuditLog
from app.models.workflow_trace import WorkflowTraceEvent
from tests.api_real.test_agent_delegation_bridge_api import _client, _create_delegation

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_b5_cancel_persists_audit_and_trace_lineage() -> None:
    """验证取消 Delegation 同时形成审计与 Trace，并保持父子身份链路一致。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, parent_execution_id = await _create_delegation(client, f"b5-cancel-{suffix}")
        response = client.post(f"/workflows/{parent_execution_id}/delegations/{delegation_id}/cancel")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "cancelled"
        trace_id = payload["trace_id"]

    async with SessionLocal() as db:
        audit = (
            await db.execute(
                select(AuditLog)
                .where(
                    AuditLog.workflow_execution_id == uuid.UUID(parent_execution_id),
                    AuditLog.resource_id == delegation_id,
                    AuditLog.action == "workflow.delegation.cancelled",
                )
                .order_by(AuditLog.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.trace_id == trace_id
        assert audit.status == "cancelled"
        assert audit.metadata_json == {"delegation_id": delegation_id}

        trace = (
            await db.execute(
                select(WorkflowTraceEvent)
                .where(
                    WorkflowTraceEvent.execution_id == uuid.UUID(parent_execution_id),
                    WorkflowTraceEvent.event_type == "agent.delegation.cancelled",
                    WorkflowTraceEvent.trace_id == trace_id,
                )
                .order_by(WorkflowTraceEvent.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        assert trace is not None
        assert trace.status == "cancelled"
        assert trace.data == {"delegation_id": delegation_id}


@pytest.mark.asyncio
async def test_b5_delegation_lifecycle_trace_events_share_parent_trace_identity() -> None:
    """验证创建与取消事件均挂在同一父 Execution/Delegation trace_id 上。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, parent_execution_id = await _create_delegation(client, f"b5-lineage-{suffix}")
        response = client.post(f"/workflows/{parent_execution_id}/delegations/{delegation_id}/cancel")
        assert response.status_code == 200, response.text
        trace_id = response.json()["trace_id"]

    async with SessionLocal() as db:
        events = list(
            (
                await db.execute(
                    select(WorkflowTraceEvent)
                    .where(
                        WorkflowTraceEvent.execution_id == uuid.UUID(parent_execution_id),
                        WorkflowTraceEvent.trace_id == trace_id,
                    )
                    .order_by(WorkflowTraceEvent.created_at.asc())
                )
            ).scalars().all()
        )
        delegation_events = [
            event for event in events
            if (event.data or {}).get("delegation_id") == delegation_id
        ]
        event_types = {event.event_type for event in delegation_events}
        assert "agent.delegation.created" in event_types
        assert "agent.delegation.cancelled" in event_types
        assert all(event.trace_id == trace_id for event in delegation_events)
        assert all(event.execution_id == uuid.UUID(parent_execution_id) for event in delegation_events)
