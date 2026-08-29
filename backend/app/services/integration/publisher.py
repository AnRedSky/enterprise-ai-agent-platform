"""Runtime Integration Event 发布器。

职责：为 Workflow、Agent、Scheduler 等运行时领域提供统一的事务内事件写入入口。
边界：只负责构造/持久化 IntegrationEvent，不负责提交数据库事务、不负责 Webhook 投递。
设计原则：事件写入必须与产生业务事实的数据库事务共存；事件重复生产使用稳定幂等键收敛。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.contract import IntegrationEvent
from app.services.integration.repository import IntegrationEventRepository


class RuntimeIntegrationEventPublisher:
    """提供 Runtime -> Durable Integration Event 的事务内发布能力。"""

    SOURCE_WORKFLOW = "workflow-runtime"
    SOURCE_AGENT = "agent-runtime"
    SOURCE_SCHEDULER = "scheduler-runtime"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = IntegrationEventRepository()

    async def publish(
        self,
        *,
        tenant_id: uuid.UUID,
        event_type: str,
        source: str,
        subject: str,
        idempotency_key: str,
        payload: dict[str, Any],
        request_id: str | None = None,
        trace_id: str | None = None,
        occurred_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IntegrationEventRecord:
        """在当前事务中幂等写入一个 Runtime Integration Event。"""
        event = IntegrationEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            subject=subject,
            idempotency_key=idempotency_key,
            payload=payload,
            request_id=request_id,
            trace_id=trace_id,
            occurred_at=occurred_at or datetime.now(UTC),
            metadata=metadata or {},
        )
        try:
            async with self.db.begin_nested():
                record = await self.repository.create(self.db, event)
            return record
        except IntegrityError:
            result = await self.db.execute(
                select(IntegrationEventRecord).where(
                    IntegrationEventRecord.tenant_id == tenant_id,
                    IntegrationEventRecord.source == source,
                    IntegrationEventRecord.event_type == event_type,
                    IntegrationEventRecord.idempotency_key == idempotency_key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                raise
            return existing

    async def publish_agent_tool(
        self, *, tenant_id: uuid.UUID, execution_id: Any, agent_id: Any, tool_id: Any,
        status: str, request_id: str | None = None, trace_id: str | None = None,
        error_code: str | None = None, metadata: dict[str, Any] | None = None,
    ) -> IntegrationEventRecord:
        """发布 Agent Tool 执行事实；不写入工具参数/结果等敏感业务数据。"""
        event_type = f"agent.tool.{status}"
        payload = {"execution_id": str(execution_id) if execution_id is not None else None,
                   "agent_id": str(agent_id), "tool_id": str(tool_id)}
        if error_code:
            payload["error_code"] = error_code
        return await self.publish(
            tenant_id=tenant_id, event_type=event_type, source=self.SOURCE_AGENT,
            subject=f"tool:{tool_id}", idempotency_key=f"tool:{execution_id}:{tool_id}:{status}",
            payload=payload, request_id=request_id, trace_id=trace_id, metadata=metadata,
        )

    async def publish_agent_retrieval(
        self, *, tenant_id: uuid.UUID, execution_id: Any, agent_id: Any,
        knowledge_source_id: Any, status: str, result_count: int | None = None,
        request_id: str | None = None, trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IntegrationEventRecord:
        """发布 Agent Retrieval 事实，只记录来源和计数，不泄漏检索内容。"""
        payload = {"execution_id": str(execution_id) if execution_id is not None else None,
                   "agent_id": str(agent_id), "knowledge_source_id": str(knowledge_source_id)}
        if result_count is not None:
            payload["result_count"] = result_count
        return await self.publish(
            tenant_id=tenant_id, event_type=f"agent.retrieval.{status}", source=self.SOURCE_AGENT,
            subject=f"knowledge:{knowledge_source_id}", idempotency_key=f"retrieval:{execution_id}:{knowledge_source_id}:{status}",
            payload=payload, request_id=request_id, trace_id=trace_id, metadata=metadata,
        )

    async def publish_agent_model(
        self, *, tenant_id: uuid.UUID, execution_id: Any, agent_id: Any,
        provider_id: Any, profile_id: Any | None, status: str,
        model_name: str | None = None, request_id: str | None = None,
        trace_id: str | None = None, error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IntegrationEventRecord:
        """发布 Model Provider 调用事实，避免把 prompt/completion 写入集成事件。"""
        payload = {"execution_id": str(execution_id) if execution_id is not None else None,
                   "agent_id": str(agent_id), "provider_id": str(provider_id),
                   "profile_id": str(profile_id) if profile_id is not None else None}
        if model_name:
            payload["model_name"] = model_name
        if error_code:
            payload["error_code"] = error_code
        return await self.publish(
            tenant_id=tenant_id, event_type=f"agent.model.{status}", source=self.SOURCE_AGENT,
            subject=f"model:{profile_id or provider_id}", idempotency_key=f"model:{execution_id}:{profile_id or provider_id}:{status}",
            payload=payload, request_id=request_id, trace_id=trace_id, metadata=metadata,
        )

    async def publish_scheduler(
        self, *, tenant_id: uuid.UUID, trigger_id: Any, status: str,
        schedule_id: Any | None = None, execution_id: Any | None = None,
        slot_key: str | None = None, request_id: str | None = None,
        trace_id: str | None = None, payload: dict[str, Any] | None = None,
    ) -> IntegrationEventRecord:
        """发布 Scheduler lease/竞争/misfire/recovery/dispatched/failure 事实。"""
        body = {"trigger_id": str(trigger_id),
                "schedule_id": str(schedule_id) if schedule_id is not None else None,
                "execution_id": str(execution_id) if execution_id is not None else None}
        if slot_key is not None:
            body["slot_key"] = slot_key
        if payload:
            body.update(payload)
        return await self.publish(
            tenant_id=tenant_id, event_type=f"scheduler.{status}", source=self.SOURCE_SCHEDULER,
            subject=f"trigger:{trigger_id}", idempotency_key=f"scheduler:{trigger_id}:{slot_key or schedule_id}:{status}",
            payload=body, request_id=request_id, trace_id=trace_id,
        )


__all__ = ["RuntimeIntegrationEventPublisher"]
