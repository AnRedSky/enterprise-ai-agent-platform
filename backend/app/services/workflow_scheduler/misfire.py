from __future__ import annotations

from typing import Sequence

from .models import MisfirePolicy, ScheduleSlot


def choose_misfire_slots(
    missed_slots: Sequence[ScheduleSlot],
    policy: MisfirePolicy,
    *,
    catch_up_limit: int = 10,
) -> tuple[ScheduleSlot, ...]:
    """根据 Contract 决定错过槽位的补偿集合，不执行数据库或 Runtime 操作。"""
    ordered = tuple(sorted(missed_slots, key=lambda item: item.planned_at))
    if not ordered or policy is MisfirePolicy.SKIP:
        return ()
    if policy is MisfirePolicy.FIRE_ONCE:
        return (ordered[0],)
    if catch_up_limit < 1:
        raise ValueError("catch_up_limit 必须大于等于 1")
    return ordered[:catch_up_limit]
