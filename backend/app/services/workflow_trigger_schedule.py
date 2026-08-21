from __future__ import annotations

import hashlib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class ScheduledTriggerConfig(BaseModel):
    """Persisted contract for the first scheduled Trigger implementation."""

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


class WebhookTriggerConfig(BaseModel):
    """Persisted webhook contract. The secret is stored only as a SHA-256 hash."""

    auth_mode: str = Field(default="secret", min_length=1, max_length=20)
    secret_hash: str = Field(min_length=64, max_length=64)
    event_id_field: str = Field(default="event_id", min_length=1, max_length=100)

    @field_validator("auth_mode")
    @classmethod
    def validate_auth_mode(cls, value: str) -> str:
        if value != "secret":
            raise ValueError("Webhook auth_mode 当前必须为 secret")
        return value


def validate_trigger_config(trigger_type: str, config: dict) -> dict:
    """Validate and normalize Trigger config without creating an execution."""
    if trigger_type == "manual":
        return config
    if trigger_type == "scheduled":
        return ScheduledTriggerConfig.model_validate(config).model_dump()
    if trigger_type == "webhook":
        candidate = dict(config or {})
        secret = candidate.pop("secret", None)
        if secret is not None:
            if not isinstance(secret, str) or len(secret) < 16 or len(secret) > 256:
                raise ValueError("Webhook secret 长度必须为 16-256 个字符")
            candidate["secret_hash"] = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        return WebhookTriggerConfig.model_validate(candidate).model_dump()
    raise ValueError(f"不支持的 Trigger type: {trigger_type}")


def verify_webhook_secret(config: dict, supplied_secret: str | None) -> bool:
    if not supplied_secret:
        return False
    expected = str((config or {}).get("secret_hash", ""))
    if len(expected) != 64:
        return False
    actual = hashlib.sha256(supplied_secret.encode("utf-8")).hexdigest()
    return actual == expected
