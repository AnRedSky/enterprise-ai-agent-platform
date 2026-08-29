"""Worker Service 进程入口。

职责：独立启动 Workflow Worker，消费 PostgreSQL 中由 Scheduler/其他入口创建的 pending Execution。
边界：不启动 FastAPI、不执行 Scheduler slot 计算、不复制 Workflow Runtime。
关键依赖：`app.services.workflow_worker.WorkflowWorker` 与数据库连接池。
"""

from __future__ import annotations

import asyncio
import logging

from app.infrastructure.db.session import engine
from app.services.workflow_worker import WorkflowWorker

logger = logging.getLogger(__name__)


async def _dispose_database_engine() -> None:
    """在 Worker 事件循环关闭前释放 SQLAlchemy 异步连接池。

    Returns:
        None。

    设计意图：Worker 进程退出时必须先让所有 Worker task 完成 Session 上下文退出，再显式
    dispose AsyncEngine。否则 asyncpg 连接可能在事件循环已经进入取消阶段时才由连接池
    异步关闭，从而出现 `asyncio.CancelledError` 的连接关闭异常。
    """
    try:
        await engine.dispose()
    except asyncio.CancelledError:
        # 退出路径已经收到取消信号时，先恢复当前协程的清理机会，再执行一次连接池释放。
        await engine.dispose()
        raise


async def run_worker_service() -> None:
    """启动独立 Worker Service，并在退出前释放数据库连接池。

    Returns:
        None。Worker 仅在进程停止时结束。

    事务边界：Worker Runtime 自己负责每个 Session 的短事务；本函数只负责进程级连接池生命周期。
    """
    worker = WorkflowWorker()
    try:
        logger.info("Worker Service started", extra={"worker_owner": worker.owner})
        await worker.run_forever()
    finally:
        worker.stop()
        await _dispose_database_engine()
        logger.info("Worker Service stopped", extra={"worker_owner": worker.owner})


def main() -> None:
    """运行 Worker Service 进程入口。"""
    try:
        asyncio.run(run_worker_service())
    except KeyboardInterrupt:
        logger.info("Worker Service received shutdown signal")
