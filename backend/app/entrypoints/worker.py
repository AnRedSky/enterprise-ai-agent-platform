"""Worker Service 进程入口。

职责：独立启动 Workflow Worker 与 Webhook Delivery Worker。
边界：不启动 FastAPI、不执行 Scheduler slot 计算；两个 Worker 均消费 PostgreSQL Durable Fact。
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from app.infrastructure.db.session import engine
from app.services.integration.webhook_delivery import WebhookDeliveryWorker
from app.services.integration.webhook_provider import WebhookHTTPProvider
from app.services.workflow_worker import WorkflowWorker

logger = logging.getLogger(__name__)


def _positive_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} 必须大于 0")
    return parsed


def _positive_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{name} 必须大于 0")
    return parsed


def _optional_uuid_env(name: str) -> uuid.UUID | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        return uuid.UUID(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} 必须是有效 UUID") from exc


def _consumer_group_env(name: str = "WEBHOOK_WORKER_CONSUMER_GROUP") -> str:
    value = os.getenv(name, WebhookDeliveryWorker.DEFAULT_CONSUMER_GROUP).strip()
    if not value or len(value) > 128:
        raise ValueError(f"{name} 必须为 1..128 个字符")
    return value


async def _dispose_database_engine() -> None:
    """在 Worker 事件循环关闭前可靠释放 SQLAlchemy 异步连接池。"""
    dispose_task = asyncio.create_task(engine.dispose())
    cancellation_requested = False
    try:
        await asyncio.shield(dispose_task)
    except asyncio.CancelledError:
        cancellation_requested = True
        task = asyncio.current_task()
        if task is not None:
            while task.cancelling():
                task.uncancel()
        await dispose_task

    if cancellation_requested:
        raise asyncio.CancelledError


async def run_worker_service() -> None:
    """启动 Workflow + Webhook Worker，并在退出时 graceful drain 后释放连接池。"""
    workflow_worker = WorkflowWorker()
    webhook_worker = WebhookDeliveryWorker(
        sender=WebhookHTTPProvider().send,
        concurrency=_positive_int_env("WEBHOOK_WORKER_CONCURRENCY", WebhookDeliveryWorker.DEFAULT_CONCURRENCY),
        lease_seconds=_positive_int_env("WEBHOOK_WORKER_LEASE_SECONDS", 60),
        max_attempts=_positive_int_env("WEBHOOK_WORKER_MAX_ATTEMPTS", 5),
        tenant_id=_optional_uuid_env("WEBHOOK_WORKER_TENANT_ID"),
        consumer_group=_consumer_group_env(),
    )
    webhook_poll_interval = _positive_float_env("WEBHOOK_WORKER_POLL_INTERVAL", 0.2)
    workflow_task = asyncio.create_task(workflow_worker.run_forever())
    webhook_task = asyncio.create_task(webhook_worker.run_forever(webhook_poll_interval))
    try:
        logger.info(
            "Worker Service started",
            extra={
                "worker_owner": workflow_worker.owner,
                "webhook_worker_owner": webhook_worker.owner,
                "webhook_concurrency": webhook_worker.concurrency,
                "webhook_tenant_id": str(webhook_worker.tenant_id) if webhook_worker.tenant_id else None,
                "webhook_consumer_group": webhook_worker.consumer_group,
            },
        )
        await asyncio.gather(workflow_task, webhook_task)
    finally:
        workflow_worker.stop()
        webhook_worker.stop()
        await asyncio.gather(workflow_task, webhook_task, return_exceptions=True)
        await _dispose_database_engine()
        logger.info(
            "Worker Service stopped",
            extra={
                "worker_owner": workflow_worker.owner,
                "webhook_worker_owner": webhook_worker.owner,
                "webhook_consumer_group": webhook_worker.consumer_group,
            },
        )


def main() -> None:
    """运行 Worker Service 进程入口。"""
    try:
        asyncio.run(run_worker_service())
    except KeyboardInterrupt:
        logger.info("Worker Service received shutdown signal")
