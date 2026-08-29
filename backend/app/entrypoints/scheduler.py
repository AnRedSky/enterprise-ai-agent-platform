"""Scheduler Service 进程入口。

职责：独立启动持久化 Scheduled Trigger Scheduler、Durable Recovery Scan、Runtime Alert Scheduler 与 Notification Routing Scheduler，使调度、恢复、运维告警和通知路由周期任务与 API HTTP 进程解耦。
边界：不提供 HTTP 路由、不复制调度或恢复规则；具体 slot、lease、misfire、Recovery Policy、告警评估与通知事件分发继续由正式领域服务负责。
关键依赖：项目配置、`app.services.workflow_scheduler`、`app.services.runtime_operations` 与 `app.services.integration` 正式入口。
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.runtime_operations.notification_scheduler import RuntimeNotificationScheduler
from app.services.runtime_operations.scheduler import RuntimeAlertScheduler
from app.services.workflow_scheduler import ScheduledTriggerScheduler
from app.services.workflow_scheduler.recovery import WorkflowRecoveryScheduler

logger = logging.getLogger(__name__)


async def _run_recovery_service(recovery_scheduler: WorkflowRecoveryScheduler) -> None:
    """运行 Recovery Scan 生命周期。"""
    await recovery_scheduler.run_forever()


async def _run_runtime_alert_service(alert_scheduler: RuntimeAlertScheduler) -> None:
    """运行 Runtime Metrics / Alert 周期任务。"""
    await alert_scheduler.run_forever()


async def _run_notification_service(notification_scheduler: RuntimeNotificationScheduler) -> None:
    """运行 Durable Integration Event -> Delivery Fact 路由周期任务。"""
    await notification_scheduler.run_forever()


async def run_scheduler_service() -> None:
    """启动并监督独立 Scheduler Service 的全部后台生命周期。

    三个领域循环共同组成既有调度职责；Notification Routing Scheduler 作为
    Integration Event -> Delivery Fact 的周期编排加入同一 Supervisor。任一循环
    发生未处理异常时统一取消其他任务并传播异常，避免服务处于半存活状态。
    """
    scheduler = ScheduledTriggerScheduler(settings.scheduler_poll_interval_seconds)
    recovery_scheduler = WorkflowRecoveryScheduler(
        poll_interval_seconds=settings.scheduler_poll_interval_seconds,
    )
    alert_scheduler = RuntimeAlertScheduler(settings.scheduler_poll_interval_seconds)
    notification_scheduler = RuntimeNotificationScheduler(settings.scheduler_poll_interval_seconds)

    scheduler_task = asyncio.create_task(scheduler.run_forever())
    recovery_task = asyncio.create_task(_run_recovery_service(recovery_scheduler))
    alert_task = asyncio.create_task(_run_runtime_alert_service(alert_scheduler))
    notification_task = asyncio.create_task(_run_notification_service(notification_scheduler))
    tasks = {scheduler_task, recovery_task, alert_task, notification_task}
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
        alert_scheduler.stop()
        notification_scheduler.stop()
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
