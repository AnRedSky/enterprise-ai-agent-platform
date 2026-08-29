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
    """在 Worker 事件循环关闭前可靠释放 SQLAlchemy 异步连接池。

    Returns:
        None。

    设计意图：Worker 退出时必须让 AsyncEngine 在事件循环仍可用期间完成连接池关闭。
    资源清理本身不应因为主 Task 的取消请求而被中断，因此使用 shield 让 dispose 操作继续执行；
    如果主 Task 已进入 cancelling 状态，则先消费当前取消计数，再等待同一个 dispose 操作完成。
    清理结束后恢复原取消语义，避免吞掉上层停止流程的 cancellation。

    Raises:
        asyncio.CancelledError: 连接池清理完成后恢复此前收到的取消请求。
    """
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
