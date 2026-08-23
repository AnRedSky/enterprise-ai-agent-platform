from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import ScheduleSlot


def normalize_utc(value: datetime) -> datetime:
    """将带时区时间转换为 UTC；禁止把无时区时间静默解释成服务器本地时间。"""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("调度时间必须包含明确时区")
    return value.astimezone(timezone.utc)


def resolve_local_time(local_time: datetime, timezone_name: str) -> datetime:
    """按 IANA 时区解析本地时间；夏令时歧义固定选择第一次出现的时间。"""
    if local_time.tzinfo is not None:
        raise ValueError("local_time 必须是无时区本地时间")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone 必须是有效的 IANA 时区名称") from exc

    first = local_time.replace(tzinfo=zone, fold=0)
    second = local_time.replace(tzinfo=zone, fold=1)
    first_roundtrip = first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    second_roundtrip = second.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    if first_roundtrip != local_time and second_roundtrip != local_time:
        raise ValueError("local_time 落在夏令时跳变造成的不存在时间内")
    return normalize_utc(first)


def build_schedule_slot(trigger_id: UUID, planned_at: datetime) -> ScheduleSlot:
    """构造标准化的调度槽位，统一使用 UTC 生成幂等键。"""
    return ScheduleSlot(trigger_id=trigger_id, planned_at=normalize_utc(planned_at))
