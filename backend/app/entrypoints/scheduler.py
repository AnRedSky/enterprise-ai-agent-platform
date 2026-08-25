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

    Scheduler Service 的进程身份由 `run_scheduler.py` 唯一确定，不再通过配置开关决定是否启动。
    这样可以保证 `run.py` 永远是 API Service，而 `run_scheduler.py` 永远是 Scheduler Service。

    Args:
        无。运行参数统一从项目配置读取，避免为 Scheduler 建立第二套配置入口。

    Returns:
        None。Scheduler 仅在进程收到停止信号时结束。

    Raises:
        无。进程级停止由事件循环和 `ScheduledTriggerScheduler` 自身负责。
    """
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
