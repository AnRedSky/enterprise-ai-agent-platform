"""Scheduler Runtime 的 trace-aware 入口。

职责：保持调度领域逻辑不变，仅在 package-level runtime 入口增加一次 scan 生命周期的统一 Recovery Telemetry。
边界：不复制 Scheduler 的候选选择、租约、misfire 或 dispatch 规则。
关键依赖：ScheduledTriggerScheduler、WorkflowSchedulerTraceService。
"""

from __future__ import annotations

from datetime import datetime

from .runtime import ScheduledTriggerScheduler as _ScheduledTriggerScheduler
from .trace import WorkflowSchedulerTraceService


class TracedScheduledTriggerScheduler(_ScheduledTriggerScheduler):
    """为 ScheduledTriggerScheduler 增加统一 scan trace 生命周期。"""

    def __init__(self, *args, trace_service: WorkflowSchedulerTraceService | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.trace_service = trace_service or WorkflowSchedulerTraceService()

    async def tick_once(self, now: datetime | None = None) -> dict[str, int]:
        """执行一轮 Scheduler scan，并保证成功或失败都结束对应 trace。

        Args:
            now: 可选的调度基准时间。

        Returns:
            本轮 Scheduler scan 的统计计数。

        Raises:
            Exception: 底层 Scheduler scan 失败时原样向调用方传播。
        """
        context = self.trace_service.start_scan()
        counters: dict[str, int] | None = None
        try:
            # 使用位置参数调用父类，避免测试/装饰器替换父类 tick_once 时出现重复绑定 now。
            counters = await super().tick_once(now)
            self.trace_service.finish_scan(
                context,
                candidates=counters.get("eligible", 0),
                eligible=counters.get("eligible", 0),
                recovered=counters.get("recovered", 0),
                contention=counters.get("contention", 0),
                failed=counters.get("failed", 0),
            )
            return counters
        except Exception:
            self.trace_service.finish_scan(context, failed=1)
            raise
