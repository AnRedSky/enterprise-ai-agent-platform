"""Scheduled Trigger 配置单元测试：验证 misfire 配置进入既有 Trigger Contract。

职责：验证 scheduled Trigger 的 timezone、interval、misfire policy 与 catch_up_limit 边界。
边界：不创建数据库记录，不执行 Scheduler Runtime。
关键依赖：`app.services.trigger.schedule.validate_trigger_config`。
"""

import pytest

from app.services.trigger.schedule import validate_trigger_config


def test_scheduled_trigger_defaults_to_skip_misfire() -> None:
    config = validate_trigger_config(
        "scheduled",
        {"timezone": "UTC", "interval_seconds": 300},
    )
    assert config["misfire_policy"] == "skip"
    assert config["catch_up_limit"] == 10


def test_scheduled_trigger_accepts_bounded_catch_up() -> None:
    config = validate_trigger_config(
        "scheduled",
        {
            "timezone": "UTC",
            "interval_seconds": 300,
            "misfire_policy": "catch_up",
            "catch_up_limit": 5,
        },
    )
    assert config["misfire_policy"] == "catch_up"
    assert config["catch_up_limit"] == 5


def test_scheduled_trigger_rejects_catch_up_limit_for_fire_once() -> None:
    with pytest.raises(ValueError, match="只有 catch_up 策略"):
        validate_trigger_config(
            "scheduled",
            {
                "timezone": "UTC",
                "interval_seconds": 300,
                "misfire_policy": "fire_once",
                "catch_up_limit": 5,
            },
        )
