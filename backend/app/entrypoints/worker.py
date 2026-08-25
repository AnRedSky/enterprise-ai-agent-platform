"""Worker Service 进程入口。

职责：独立启动 Workflow Worker，消费 PostgreSQL 中由 Scheduler/其他入口创建的 pending Execution。
边界：不启动 FastAPI、不执行 Scheduler slot 计算、不复制 Workflow Runtime。
关键依赖：`app.services.workflow_worker.WorkflowWorker`。
"""

from __future__ import annotations

import asyncio
import logging

from app.services.workflow_worker import WorkflowWorker

logger = logging.getLogger(__name__)


async def run_worker_service() -> None:
    """启动独立 Worker Service。

    Returns:
        None。Worker 仅在进程停止时结束。
    """
    worker = WorkflowWorker()
    try:
        logger.info("Worker Service started", extra={"worker_owner": worker.owner})
        await worker.run_forever()
    finally:
        worker.stop()
        logger.info("Worker Service stopped", extra={"worker_owner": worker.owner})


def main() -> None:
    """运行 Worker Service 进程入口。"""
    try:
        asyncio.run(run_worker_service())
    except KeyboardInterrupt:
        logger.info("Worker Service received shutdown signal")
