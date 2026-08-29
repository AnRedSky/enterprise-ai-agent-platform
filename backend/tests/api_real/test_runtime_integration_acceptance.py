"""Phase 2.9-E Runtime Integration real PostgreSQL acceptance.

The test owns fixture tenants and verifies the five runtime event families are durably stored
under the correct tenant. It never starts API, Worker, Scheduler, Redis or PostgreSQL services.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.integration_event import IntegrationEventRecord
from app.services.integration.publisher import RuntimeIntegrationEventPublisher

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_runtime_integration_five_domain_facts_are_durable_and_tenant_scoped() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    execution_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    knowledge_source_id = uuid.uuid4()
    provider_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    trigger_id = uuid.uuid4()
    schedule_id = uuid.uuid4()
    expected = {
        "workflow.execution.completed",
        "agent.tool.succeeded",
        "agent.retrieval.succeeded",
        "agent.model.succeeded",
        "scheduler.dispatched",
    }
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-29-runtime-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-29-runtime-b-{suffix}", status="active"),
            ])
            publisher = RuntimeIntegrationEventPublisher(db)
            now = datetime.now(UTC)
            await publisher.publish(
                tenant_id=tenant_a,
                event_type="workflow.execution.completed",
                source=publisher.SOURCE_WORKFLOW,
                subject=f"execution:{execution_id}",
                idempotency_key=f"acceptance:workflow:{suffix}",
                payload={"execution_id": str(execution_id), "status": "completed"},
                occurred_at=now,
            )
            await publisher.publish_agent_tool(
                tenant_id=tenant_a, execution_id=execution_id, agent_id=agent_id,
                tool_id=tool_id, status="succeeded",
            )
            await publisher.publish_agent_retrieval(
                tenant_id=tenant_a, execution_id=execution_id, agent_id=agent_id,
                knowledge_source_id=knowledge_source_id, status="succeeded", result_count=3,
            )
            await publisher.publish_agent_model(
                tenant_id=tenant_a, execution_id=execution_id, agent_id=agent_id,
                provider_id=provider_id, profile_id=profile_id, status="succeeded",
                model_name="acceptance-model", metadata={"prompt_tokens": 12, "completion_tokens": 7},
            )
            await publisher.publish_scheduler(
                tenant_id=tenant_a, trigger_id=trigger_id, schedule_id=schedule_id,
                execution_id=execution_id, slot_key=f"acceptance:{suffix}", status="dispatched",
                payload={"recovery": False},
            )
            await publisher.publish(
                tenant_id=tenant_b,
                event_type="workflow.execution.completed",
                source=publisher.SOURCE_WORKFLOW,
                subject=f"execution:{execution_id}",
                idempotency_key=f"acceptance:workflow:{suffix}:tenant-b",
                payload={"execution_id": str(execution_id), "status": "completed"},
                occurred_at=now,
            )
            await db.commit()

        async with SessionLocal() as db:
            tenant_a_events = list((await db.execute(
                select(IntegrationEventRecord)
                .where(IntegrationEventRecord.tenant_id == tenant_a)
                .order_by(IntegrationEventRecord.created_at.asc())
            )).scalars().all())
            tenant_b_events = list((await db.execute(
                select(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_b)
            )).scalars().all())
            assert {event.event_type for event in tenant_a_events} == expected
            assert len(tenant_a_events) == 5
            assert len(tenant_b_events) == 1
            assert all(event.tenant_id == tenant_a for event in tenant_a_events)
            assert all(event.tenant_id == tenant_b for event in tenant_b_events)

            model_event = next(event for event in tenant_a_events if event.event_type == "agent.model.succeeded")
            assert "prompt" not in model_event.payload
            assert "completion" not in model_event.payload
            assert model_event.metadata_json["prompt_tokens"] == 12

            retrieval_event = next(event for event in tenant_a_events if event.event_type == "agent.retrieval.succeeded")
            assert "content" not in retrieval_event.payload
            assert retrieval_event.payload["result_count"] == 3

            cross_tenant = await db.scalar(select(IntegrationEventRecord).where(
                IntegrationEventRecord.tenant_id == tenant_b,
                IntegrationEventRecord.id == tenant_a_events[0].id,
            ))
            assert cross_tenant is None
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(IntegrationEventRecord).where(
                IntegrationEventRecord.tenant_id.in_([tenant_a, tenant_b])
            ))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
