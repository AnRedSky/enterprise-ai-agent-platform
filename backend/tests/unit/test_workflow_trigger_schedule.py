"""验证 Trigger 配置契约、规范化以及生命周期服务的配置边界。"""

import pytest
from fastapi import HTTPException

from app.services.trigger import ScheduledTriggerConfig, WorkflowTriggerService, validate_trigger_config


def test_scheduled_trigger_config_accepts_valid_interval_and_iana_timezone():
    config = ScheduledTriggerConfig(timezone="Asia/Shanghai", interval_seconds=300)
    assert config.model_dump() == {"timezone": "Asia/Shanghai", "interval_seconds": 300}


def test_scheduled_trigger_config_rejects_invalid_timezone():
    with pytest.raises(ValueError, match="有效 IANA timezone"):
        ScheduledTriggerConfig(timezone="Not/A_Timezone", interval_seconds=300)


@pytest.mark.parametrize("interval", [59, 86401])
def test_scheduled_trigger_config_rejects_interval_outside_contract(interval):
    with pytest.raises(ValueError):
        ScheduledTriggerConfig(timezone="UTC", interval_seconds=interval)


def test_validate_trigger_config_preserves_manual_config():
    config = {"source": "manual"}
    assert validate_trigger_config("manual", config) == config


def test_validate_trigger_config_normalizes_scheduled_config():
    assert validate_trigger_config(
        "scheduled", {"timezone": "UTC", "interval_seconds": 600}
    ) == {"timezone": "UTC", "interval_seconds": 600}


def test_trigger_service_accepts_scheduled_type():
    assert WorkflowTriggerService.validate_type("scheduled") == "scheduled"


def test_trigger_service_rejects_unknown_type():
    with pytest.raises(HTTPException) as exc_info:
        WorkflowTriggerService.validate_type("event")
    assert exc_info.value.status_code == 422


def test_trigger_service_validates_scheduled_config():
    assert WorkflowTriggerService.validate_config(
        "scheduled", {"timezone": "Asia/Shanghai", "interval_seconds": 300}
    ) == {"timezone": "Asia/Shanghai", "interval_seconds": 300}


def test_trigger_service_rejects_invalid_scheduled_config():
    with pytest.raises(HTTPException) as exc_info:
        WorkflowTriggerService.validate_config(
            "scheduled", {"timezone": "UTC", "interval_seconds": 30}
        )
    assert exc_info.value.status_code == 422
