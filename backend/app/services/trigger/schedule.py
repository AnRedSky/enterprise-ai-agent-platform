"""Trigger 配置契约与校验模块。

职责：定义 scheduled/webhook Trigger 的持久化配置契约、规范化与 Webhook Secret 校验。
边界：只负责配置边界，不创建 Workflow Execution，也不负责 Trigger 生命周期持久化。
关键依赖：Pydantic 配置模型、IANA timezone 数据和 SHA-256。
"""

from __future__ import annotations

import hashlib
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class ScheduledTriggerConfig(BaseModel):
    """定义 scheduled Trigger 的调度与 misfire 配置契约。"""

    timezone: str = Field(min_length=1, max_length=64)
    interval_seconds: int = Field(ge=60, le=86400)
    misfire_policy: Literal["skip", "fire_once", "catch_up"] = "skip"
    catch_up_limit: int = Field(default=10, ge=1, le=100)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone 必须为有效 IANA timezone") from exc
        return value

    def validate_misfire_options(self) -> "ScheduledTriggerConfig":
        """确保只有 catch_up 策略可以改变补跑上限，避免产生未定义的配置组合。"""
        if self.misfire_policy != "catch_up" and self.catch_up_limit != 10:
            raise ValueError("只有 catch_up 策略允许配置 catch_up_limit")
        return self


class WebhookTriggerConfig(BaseModel):
    """定义 Webhook Trigger 配置契约；Secret 只允许以 SHA-256 摘要持久化。"""

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
    """校验并规范化 Trigger 配置，但不创建执行记录。"""
    if trigger_type == "manual":
        return config
    if trigger_type == "scheduled":
        candidate = ScheduledTriggerConfig.model_validate(config)
        candidate.validate_misfire_options()
        return candidate.model_dump()
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
    """校验请求 Secret 与持久化摘要是否一致。"""
    if not supplied_secret:
        return False
    expected = str((config or {}).get("secret_hash", ""))
    if len(expected) != 64:
        return False
    actual = hashlib.sha256(supplied_secret.encode("utf-8")).hexdigest()
    return actual == expected
