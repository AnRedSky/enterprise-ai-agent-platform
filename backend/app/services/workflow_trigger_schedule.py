from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class ScheduledTriggerConfig(BaseModel):
    """Persisted contract for the first scheduled Trigger implementation.

    This is intentionally an interval contract, not a Cron expression. A scheduler
    is responsible for interpreting this contract in a later Phase 1.7 task.
    """

    timezone: str = Field(min_length=1, max_length=64)
    interval_seconds: int = Field(ge=60, le=86400)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone 必须为有效 IANA timezone") from exc
        return value


def validate_trigger_config(trigger_type: str, config: dict) -> dict:
    """Validate and normalize Trigger config without creating an execution."""
    if trigger_type == "manual":
        return config
    if trigger_type == "scheduled":
        return ScheduledTriggerConfig.model_validate(config).model_dump()
    raise ValueError(f"不支持的 Trigger type: {trigger_type}")
