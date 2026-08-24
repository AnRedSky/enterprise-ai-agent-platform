"""Workflow Scheduler 领域模块。

职责：提供 Workflow 定时调度契约、时间槽计算、misfire 策略与调度运行入口。
边界：只负责调度领域规则与 Scheduler Runtime，不承担 Workflow 执行状态机、Trigger 业务服务或数据库基础设施实现。
关键依赖：Workflow Trigger Service、Scheduler Contract，以及持久化租约所需的数据库 Session。
"""

from .contract import (
    MisfirePolicy,
    ScheduleSlot,
    SchedulerClock,
    SchedulerState,
    SchedulerStatus,
    WorkflowScheduleContract,
    build_schedule_slot,
    choose_misfire_slots,
    lease_available,
    normalize_utc,
    resolve_local_time,
)
from .runtime import ScheduledTriggerScheduler

__all__ = [
    "MisfirePolicy",
    "ScheduleSlot",
    "SchedulerClock",
    "SchedulerState",
    "SchedulerStatus",
    "WorkflowScheduleContract",
    "ScheduledTriggerScheduler",
    "build_schedule_slot",
    "choose_misfire_slots",
    "lease_available",
    "normalize_utc",
    "resolve_local_time",
]
