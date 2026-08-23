"""Scheduler Runtime 单元测试：验证持久化调度槽位的时间与幂等规则。

职责：覆盖 Runtime 的纯计算边界，不连接数据库、不模拟 Workflow 执行。
关键依赖：ScheduledTriggerScheduler。
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler


def test_planned_slot_key_is_stable_for_persisted_time() -> None:
    """相同 trigger + planned_at 必须产生相同槽位键。"""
    trigger_id = uuid4()
    planned_at = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    assert ScheduledTriggerScheduler.planned_slot_key(trigger_id, planned_at) == ScheduledTriggerScheduler.planned_slot_key(
        trigger_id, planned_at
    )


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
