"""Webhook Delivery Worker 独立服务入口。"""

from __future__ import annotations

import asyncio
import logging

from app.entrypoints.worker import _dispose_database_engine
from app.services.integration.webhook_delivery import WebhookDeliveryWorker
from app.services.integration.webhook_provider import WebhookHTTPProvider

logger = logging.getLogger(__name__)


async def run_webhook_worker_service() -> None:
    """运行 Webhook Delivery Worker，不启动 API/Scheduler。"""
    provider = WebhookHTTPProvider()
    worker = WebhookDeliveryWorker(sender=provider.send)
    try:
        logger.info("Webhook Delivery Worker started", extra={"worker_owner": worker.owner})
        await worker.run_forever()
    finally:
        worker.stop()
        await _dispose_database_engine()
        logger.info("Webhook Delivery Worker stopped", extra={"worker_owner": worker.owner})


def main() -> None:
    try:
        asyncio.run(run_webhook_worker_service())
    except KeyboardInterrupt:
        logger.info("Webhook Delivery Worker received shutdown signal")


if __name__ == "__main__":
    main()
