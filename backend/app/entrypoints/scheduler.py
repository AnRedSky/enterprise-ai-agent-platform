"""Scheduler Service 进程入口。

职责：独立启动持久化 Scheduled Trigger Scheduler，使调度循环与 API HTTP 进程解耦。
边界：不提供 HTTP 路由、不复制调度规则；具体 slot、lease、misfire、幂等与执行分发继续由
`ScheduledTriggerScheduler` 负责。
关键依赖：项目配置与 `app.services.workflow_scheduler` 正式入口。
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.workflow_scheduler import ScheduledTriggerScheduler

logger = logging.getLogger(__name__)


async def run_scheduler_service() -> None:
    """启动并持续运行独立 Scheduler Service。

    Args:
        无。运行参数统一从项目配置读取，避免为 Scheduler 建立第二套配置入口。

    Returns:
        None。Scheduler 仅在进程收到停止信号或运行配置关闭时结束。

    Raises:
        RuntimeError: 当 Scheduler Service 被显式关闭配置时拒绝启动。

    重要副作用：持续访问 PostgreSQL 并创建 Scheduled Trigger execution；进程退出前通过
    `stop()` 请求 Scheduler 完成当前轮询并释放生命周期资源。
    """
    if not settings.scheduler_enabled:
        raise RuntimeError("Scheduler Service 已被 scheduler_enabled 配置关闭")

    scheduler = ScheduledTriggerScheduler(settings.scheduler_poll_interval_seconds)
    try:
        logger.info("Scheduler Service started")
        await scheduler.run_forever()
    finally:
        scheduler.stop()
        logger.info("Scheduler Service stopped")


def main() -> None:
    """运行 Scheduler Service 进程入口。"""
    try:
        asyncio.run(run_scheduler_service())
    except KeyboardInterrupt:
        logger.info("Scheduler Service received shutdown signal")
