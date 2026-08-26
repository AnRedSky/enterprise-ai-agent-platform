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

    事务边界：Recovery Scheduler 自己管理每轮数据库 Session；入口只负责进程级并发生命周期。
    """
    await recovery_scheduler.run_forever()


async def run_scheduler_service() -> None:
    """启动并持续运行独立 Scheduler Service。

    Scheduler Service 同时运行 Scheduled Trigger Dispatch 与 Durable Recovery Scan 两条独立循环；
    两者共享进程但不共享数据库 Session，也不互相复制业务规则。

    Args:
        无。运行参数统一从项目配置读取，避免为 Scheduler 建立第二套配置入口。

    Returns:
        None。Scheduler 仅在进程收到停止信号时结束。

    Raises:
        无。进程级停止由事件循环以及两个领域 Scheduler 自身负责。
    """
    scheduler = ScheduledTriggerScheduler(settings.scheduler_poll_interval_seconds)
    recovery_scheduler = WorkflowRecoveryScheduler(
        poll_interval_seconds=settings.scheduler_poll_interval_seconds,
    )
    recovery_task = asyncio.create_task(_run_recovery_service(recovery_scheduler))
    try:
        logger.info("Scheduler Service started")
        await scheduler.run_forever()
    finally:
        scheduler.stop()
        recovery_scheduler.stop()
        recovery_task.cancel()
        try:
            await recovery_task
        except asyncio.CancelledError:
            pass
        logger.info("Scheduler Service stopped")


def main() -> None:
    """运行 Scheduler Service 进程入口。"""
    try:
        asyncio.run(run_scheduler_service())
    except KeyboardInterrupt:
        logger.info("Scheduler Service received shutdown signal")
