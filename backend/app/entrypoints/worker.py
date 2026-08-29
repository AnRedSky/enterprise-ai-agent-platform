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
    dispose AsyncEngine。若当前进程正在处理取消信号，必须暂时清除当前 Task 的 pending
    cancellation，使 asyncpg 能在事件循环仍可用时完成连接关闭；清理完成后重新抛出取消信号。
    """
    try:
        await engine.dispose()
    except asyncio.CancelledError:
        # asyncio.run 在收到终止信号时可能已经将主 Task 标记为 cancelling。若直接再次 await，
        # asyncpg 的 close 会再次被取消，最终把 CancelledError 变成连接池关闭阶段的异常日志。
        task = asyncio.current_task()
        if task is not None:
            while task.cancelling():
                task.uncancel()
        try:
            await engine.dispose()
        finally:
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
