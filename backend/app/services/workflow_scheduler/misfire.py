"""Workflow Scheduler misfire 规划模块。

职责：根据持久化 next_run_at、当前时间与 misfire policy 计算本轮允许处理的槽位。
边界：只计算调度槽位，不执行数据库写入、租约操作或 Workflow Execution。
关键依赖：Scheduler 模型定义与统一的时间槽位构造函数。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Sequence
from uuid import UUID

from .models import MisfirePolicy, ScheduleSlot
from .time import build_schedule_slot


def choose_misfire_slots(
    missed_slots: Sequence[ScheduleSlot],
    policy: MisfirePolicy,
    *,
    catch_up_limit: int = 10,
) -> tuple[ScheduleSlot, ...]:
    """根据 misfire 策略决定错过槽位的补偿集合，不执行数据库或 Runtime 操作。"""
    ordered = tuple(sorted(missed_slots, key=lambda item: item.planned_at))
    if not ordered or policy is MisfirePolicy.SKIP:
        return ()
    if policy is MisfirePolicy.FIRE_ONCE:
        return (ordered[0],)
    if catch_up_limit < 1:
        raise ValueError("catch_up_limit 必须大于等于 1")
    return ordered[:catch_up_limit]


def build_due_slots(
    trigger_id: UUID,
    next_run_at: datetime,
    now: datetime,
    interval_seconds: int,
    *,
    limit: int = 12,
) -> tuple[ScheduleSlot, ...]:
    """从持久化 next_run_at 向前生成有界到期槽位，防止长时间停机形成无限内存回放。"""
    if interval_seconds < 1:
        raise ValueError("interval_seconds 必须大于 0")
    if limit < 1:
        raise ValueError("limit 必须大于等于 1")
    start = next_run_at.astimezone(UTC) if next_run_at.tzinfo else next_run_at.replace(tzinfo=UTC)
    current = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    if start > current:
        return ()
    slots: list[ScheduleSlot] = []
    planned_at = start
    while planned_at <= current and len(slots) < limit:
        slots.append(build_schedule_slot(trigger_id, planned_at))
        planned_at += timedelta(seconds=interval_seconds)
    return tuple(slots)


def next_run_after_misfire(
    selected_slots: Sequence[ScheduleSlot],
    policy: MisfirePolicy,
    now: datetime,
    interval_seconds: int,
) -> datetime:
    """计算本轮补偿后的下一运行时间；不同策略统一回到未来调度轴。"""
    if interval_seconds < 1:
        raise ValueError("interval_seconds 必须大于 0")
    current = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    if policy in (MisfirePolicy.SKIP, MisfirePolicy.FIRE_ONCE) or not selected_slots:
        return current + timedelta(seconds=interval_seconds)
    return selected_slots[-1].planned_at + timedelta(seconds=interval_seconds)
