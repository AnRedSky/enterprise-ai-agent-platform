"""Scheduler Service 进程入口。

职责：独立启动持久化 Scheduled Trigger Scheduler 与 Durable Recovery Scan，使调度与 API HTTP 进程解耦。
边界：不提供 HTTP 路由、不复制调度或恢复规则；具体 slot、lease、misfire、Recovery Policy、幂等与执行分发继续由正式领域服务负责。
关键依赖：项目配置、`app.services.workflow_scheduler` 正式入口。
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.workflow_scheduler import ScheduledTriggerScheduler
from app.services.workflow_scheduler.recovery import WorkflowRecoveryScheduler

logger = logging.getLogger(__name__)


async def _run_recovery_service(recovery_scheduler: WorkflowRecoveryScheduler) -> None:
    """运行 Recovery Scan 生命周期。

    Args:
        recovery_scheduler: 已创建的 Recovery Scheduler 实例。

    Returns:
        None。直到收到进程停止或任务被取消。

    Raises:
        Exception: Recovery Scan 自身发生未处理异常时向 Service Supervisor 汇报。

    事务边界：Recovery Scheduler 自己管理每轮数据库 Session；入口只负责进程级并发生命周期。
    """
    await recovery_scheduler.run_forever()


async def run_scheduler_service() -> None:
    """启动并监督独立 Scheduler Service 的全部后台生命周期。

    Args:
        无。运行参数统一从项目配置读取，避免为 Scheduler 建立第二套配置入口。

    Returns:
        None。所有受监督任务正常停止后结束。

    Raises:
        Exception: Scheduled Trigger Dispatch 或 Durable Recovery Scan 任一任务发生未处理异常时，
            取消另一任务并向进程入口传播原始异常，避免服务处于“半存活”状态。

    设计意图：Scheduler Dispatch 与 Recovery Scan 是同一进程中的两个独立领域循环；任一循环失效都意味着
    Scheduler Service 已不能提供完整的 Durable 调度职责，因此必须统一失败收敛，而不是留下静默失效的后台任务。
    """
    scheduler = ScheduledTriggerScheduler(settings.scheduler_poll_interval_seconds)
    recovery_scheduler = WorkflowRecoveryScheduler(
        poll_interval_seconds=settings.scheduler_poll_interval_seconds,
    )
    scheduler_task = asyncio.create_task(scheduler.run_forever())
    recovery_task = asyncio.create_task(_run_recovery_service(recovery_scheduler))
    tasks = {scheduler_task, recovery_task}
    try:
        logger.info("Scheduler Service started")
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            exception = task.exception()
            if exception is not None:
                raise exception
        await asyncio.gather(*tasks)
    finally:
        scheduler.stop()
        recovery_scheduler.stop()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Scheduler Service stopped")


def main() -> None:
    """运行 Scheduler Service 进程入口。"""
    try:
        asyncio.run(run_scheduler_service())
    except KeyboardInterrupt:
        logger.info("Scheduler Service received shutdown signal")
