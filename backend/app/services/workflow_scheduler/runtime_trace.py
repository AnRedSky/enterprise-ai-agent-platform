"""Scheduler Runtime 的 trace-aware 入口。

保持 `runtime.py` 的调度领域逻辑不变，仅在 package-level runtime 入口增加
一次 scan 生命周期的统一 Recovery Telemetry。
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
        context = self.trace_service.start_scan()
        counters: dict[str, int] | None = None
        try:
            counters = await super().tick_once(now=now)
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
