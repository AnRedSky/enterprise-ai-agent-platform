from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol, Sequence
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class SchedulerStatus(StrEnum):
    """调度触发器的持久化状态。"""

    ENABLED = "enabled"
    PAUSED = "paused"
    DISABLED = "disabled"


class MisfirePolicy(StrEnum):
    """调度器发现历史计划槽位未执行时采用的补偿策略。"""

    SKIP = "skip"
    FIRE_ONCE = "fire_once"
    CATCH_UP = "catch_up"


class SchedulerClock(Protocol):
    """可注入的时钟协议，避免调度计算直接依赖系统当前时间。"""

    def now_utc(self) -> datetime:
        """返回带 UTC 时区信息的当前时间。"""


@dataclass(frozen=True)
class WorkflowScheduleContract:
    """已发布 Workflow 的 Scheduled Trigger 持久化 Contract。"""

    trigger_id: UUID
    workflow_id: UUID
    enabled: bool
    status: SchedulerStatus
    timezone: str
    schedule_expression: str
    next_run_at: datetime
    last_run_at: datetime | None
    last_execution_id: UUID | None
    lease_owner: str | None
    lease_expires_at: datetime | None
    misfire_policy: MisfirePolicy
    updated_at: datetime
    catch_up_limit: int = 10

    def __post_init__(self) -> None:
        """校验持久化字段的稳定边界，避免无效状态进入调度层。"""
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone 必须是有效的 IANA 时区名称") from exc
        if not self.schedule_expression.strip():
            raise ValueError("schedule_expression 不能为空")
        if self.catch_up_limit < 1:
            raise ValueError("catch_up_limit 必须大于等于 1")
        if self.misfire_policy is not MisfirePolicy.CATCH_UP and self.catch_up_limit != 10:
            raise ValueError("只有 catch_up 策略允许配置 catch_up_limit")
        if self.status is SchedulerStatus.DISABLED and self.enabled:
            raise ValueError("disabled 状态必须同时将 enabled 设为 false")
        if self.status is SchedulerStatus.ENABLED and not self.enabled:
            raise ValueError("enabled 状态必须同时将 enabled 设为 true")
        _require_utc(self.next_run_at, "next_run_at")
        _require_utc(self.updated_at, "updated_at")
        if self.last_run_at is not None:
            _require_utc(self.last_run_at, "last_run_at")
        if self.lease_expires_at is not None:
            _require_utc(self.lease_expires_at, "lease_expires_at")
        if self.lease_expires_at is not None and not self.lease_owner:
            raise ValueError("lease_expires_at 存在时必须同时存在 lease_owner")


@dataclass(frozen=True)
class SchedulerState:
    """调度器状态转换的最小 Contract，不包含数据库实现。"""

    status: SchedulerStatus
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None

    def __post_init__(self) -> None:
        """确保 lease 所有者与过期时间始终成对出现。"""
        if (self.lease_owner is None) != (self.lease_expires_at is None):
            raise ValueError("lease_owner 与 lease_expires_at 必须同时存在或同时为空")
        if self.lease_expires_at is not None:
            _require_utc(self.lease_expires_at, "lease_expires_at")


@dataclass(frozen=True)
class ScheduleSlot:
    """一个计划执行时间槽及其稳定幂等键。"""

    trigger_id: UUID
    planned_at: datetime

    def __post_init__(self) -> None:
        """计划时间必须统一为 UTC，保证不同实例生成相同幂等键。"""
        _require_utc(self.planned_at, "planned_at")

    @property
    def schedule_slot_key(self) -> str:
        """生成由 trigger 与计划时间组成的稳定调度幂等键。"""
        return f"{self.trigger_id}:{self.planned_at.isoformat()}"


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


def lease_available(now: datetime, lease_expires_at: datetime | None) -> bool:
    """判断调度槽位是否允许被当前 worker 抢占。"""
    now_utc = normalize_utc(now)
    if lease_expires_at is None:
        return True
    return normalize_utc(lease_expires_at) <= now_utc


def choose_misfire_slots(
    missed_slots: Sequence[ScheduleSlot],
    policy: MisfirePolicy,
    *,
    catch_up_limit: int = 10,
) -> tuple[ScheduleSlot, ...]:
    """根据 Contract 决定错过槽位的补偿集合，不执行任何数据库或 Runtime 操作。"""
    ordered = tuple(sorted(missed_slots, key=lambda item: item.planned_at))
    if not ordered or policy is MisfirePolicy.SKIP:
        return ()
    if policy is MisfirePolicy.FIRE_ONCE:
        return (ordered[0],)
    if catch_up_limit < 1:
        raise ValueError("catch_up_limit 必须大于等于 1")
    return ordered[:catch_up_limit]


def _require_utc(value: datetime, field_name: str) -> None:
    """确保持久化时间字段带有明确的 UTC 时区信息。"""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} 必须包含明确时区")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} 必须使用 UTC")
