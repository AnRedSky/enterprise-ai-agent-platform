"""Workflow Scheduler misfire 纯规则单元测试。

职责：锁定 skip / fire_once / catch_up 的槽位选择与下一次运行时间语义。
边界：不访问数据库、不启动服务、不复制生产计算逻辑。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.services.workflow_scheduler.misfire import build_due_slots, choose_misfire_slots, next_run_after_misfire
from app.services.workflow_scheduler.models import MisfirePolicy


@pytest.fixture
def trigger_id():
    """为每个测试生成独立 Trigger 身份，避免共享固定测试数据。"""
    return uuid4()


def test_skip_discards_all_missed_slots() -> None:
    """skip 必须丢弃全部历史积压，并由 Runtime 将调度轴推进到未来。"""
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    slots = build_due_slots(uuid4(), now - timedelta(minutes=3), now, 60, limit=10)

    selected = choose_misfire_slots(slots, MisfirePolicy.SKIP)

    assert len(slots) == 4
    assert selected == ()
    assert next_run_after_misfire(selected, MisfirePolicy.SKIP, now, 60) == now + timedelta(seconds=60)


def test_fire_once_selects_oldest_missed_slot_and_skips_remaining_backlog() -> None:
    """fire_once 只补一次，且选择有序积压中的最早槽位；剩余积压不在本轮重复执行。"""
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    slots = build_due_slots(uuid4(), now - timedelta(minutes=3), now, 60, limit=10)

    selected = choose_misfire_slots(slots, MisfirePolicy.FIRE_ONCE)

    assert len(selected) == 1
    assert selected[0] == slots[0]
    assert next_run_after_misfire(selected, MisfirePolicy.FIRE_ONCE, now, 60) == now + timedelta(seconds=60)


def test_catch_up_respects_limit_and_leaves_remaining_backlog_for_next_tick() -> None:
    """catch_up 只处理本轮上限，下一运行时间沿最后一个已处理槽位继续。"""
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    slots = build_due_slots(uuid4(), now - timedelta(minutes=5), now, 60, limit=10)

    selected = choose_misfire_slots(slots, MisfirePolicy.CATCH_UP, catch_up_limit=2)

    assert len(slots) == 6
    assert selected == slots[:2]
    assert next_run_after_misfire(selected, MisfirePolicy.CATCH_UP, now, 60) == slots[1].planned_at + timedelta(seconds=60)


def test_catch_up_requires_positive_limit() -> None:
    """catch_up 的处理上限必须为正数，避免形成无意义的无限回放配置。"""
    with pytest.raises(ValueError, match="catch_up_limit"):
        choose_misfire_slots((), MisfirePolicy.CATCH_UP, catch_up_limit=0)


def test_due_slot_generation_is_bounded() -> None:
    """长时间停机时槽位生成必须受 limit 限制，不能随停机时长无限增长。"""
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    slots = build_due_slots(uuid4(), now - timedelta(days=30), now, 60, limit=3)

    assert len(slots) == 3
    assert slots[0].planned_at == now - timedelta(days=30)
    assert slots[-1].planned_at == slots[0].planned_at + timedelta(minutes=2)
