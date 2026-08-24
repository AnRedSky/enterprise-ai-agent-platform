"""Scheduler Runtime 单元测试：验证持久化调度槽位的时间、幂等与 misfire 规划规则。

职责：覆盖 Runtime 与 misfire 的纯计算边界，不连接数据库、不模拟 Workflow 执行。
关键依赖：ScheduledTriggerScheduler、Scheduler misfire 规划模块。
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.workflow_scheduler.misfire import build_due_slots, next_run_after_misfire
from app.services.workflow_scheduler.models import MisfirePolicy
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler


def test_planned_slot_key_is_stable_for_persisted_time() -> None:
    """相同 trigger + planned_at + interval 必须产生相同槽位键。"""
    trigger_id = uuid4()
    planned_at = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    assert ScheduledTriggerScheduler.planned_slot_key(trigger_id, planned_at, 300) == ScheduledTriggerScheduler.planned_slot_key(
        trigger_id, planned_at, 300
    )


def test_planned_slot_key_matches_public_idempotency_key() -> None:
    """Runtime 内部槽位键必须与公开 Scheduler Contract 使用同一 interval slot 键空间。"""
    trigger_id = uuid4()
    planned_at = datetime(2026, 8, 23, 12, 0, 37, tzinfo=UTC)
    assert ScheduledTriggerScheduler.planned_slot_key(trigger_id, planned_at, 60) == ScheduledTriggerScheduler.idempotency_key(
        trigger_id, planned_at, 60
    )


def test_current_interval_slot_is_not_marked_as_recovery() -> None:
    """当前 interval 槽位即使其计划时间早于 now，也不能被误标为历史 recovery。"""
    now = datetime(2026, 8, 23, 12, 0, 37, tzinfo=UTC)
    current_slot = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    historical_slot = current_slot - timedelta(seconds=60)

    assert ScheduledTriggerScheduler.is_recovery_slot(current_slot, now, 60) is False
    assert ScheduledTriggerScheduler.is_recovery_slot(historical_slot, now, 60) is True


def test_next_run_after_skip_drops_historical_backlog() -> None:
    """首版 skip 策略不得因为 worker 停机而连续补发历史槽位。"""
    now = datetime(2026, 8, 23, 12, 10, tzinfo=UTC)
    planned_at = now - timedelta(minutes=30)
    assert ScheduledTriggerScheduler.next_run_after_skip(planned_at, now, 300) == now + timedelta(seconds=300)


def test_next_run_after_skip_preserves_future_slot() -> None:
    """未形成积压时保持原有 interval 计划。"""
    now = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    planned_at = now - timedelta(seconds=60)
    assert ScheduledTriggerScheduler.next_run_after_skip(planned_at, now, 300) == datetime(
        2026, 8, 23, 12, 4, tzinfo=UTC
    )


def test_parse_interval_rejects_unknown_expression() -> None:
    """Scheduler 只解析自身产生的持久化表达式，避免引入第二套调度语法。"""
    try:
        ScheduledTriggerScheduler.parse_interval("*/5 * * * *")
    except ValueError as exc:
        assert "不支持" in str(exc)
    else:
        raise AssertionError("应拒绝非 interval Scheduler expression")


def test_build_due_slots_is_bounded_for_long_scheduler_outage() -> None:
    """长时间停机只生成有界槽位集合，避免 catch_up 形成无界内存回放。"""
    trigger_id = uuid4()
    start = datetime(2026, 8, 23, 0, 0, tzinfo=UTC)
    now = start + timedelta(hours=24)
    slots = build_due_slots(trigger_id, start, now, 60, limit=12)
    assert len(slots) == 12
    assert slots[0].planned_at == start
    assert slots[-1].planned_at == start + timedelta(minutes=11)


def test_fire_once_misfire_returns_to_future_schedule() -> None:
    """fire_once 只补一次，随后直接回到未来 interval，不能在下一 tick 重放历史积压。"""
    trigger_id = uuid4()
    start = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    now = start + timedelta(minutes=30)
    slots = build_due_slots(trigger_id, start, now, 300, limit=12)
    selected = (slots[0],)
    assert next_run_after_misfire(selected, MisfirePolicy.FIRE_ONCE, now, 300) == now + timedelta(seconds=300)


def test_catch_up_misfire_preserves_remaining_backlog_after_limit() -> None:
    """catch_up 达到上限时保留下一未处理槽位，下一 tick 可以继续有界补跑。"""
    trigger_id = uuid4()
    start = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    now = start + timedelta(minutes=30)
    slots = build_due_slots(trigger_id, start, now, 300, limit=12)
    selected = slots[:3]
    assert next_run_after_misfire(selected, MisfirePolicy.CATCH_UP, now, 300) == start + timedelta(minutes=15)
