from __future__ import annotations

import asyncio
import random
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion, User
from app.models.organization import Organization
from app.runtime.model import ModelGateway
from app.schemas.model_provider import ModelProviderRoutingRequest
from app.services.circuit_breaker import CircuitBreakerService, CircuitOpenError
from app.services.model import RuntimeModelGovernanceService


class WorkflowRuntime:
    """Execute the stable Phase 1.5-D sequential workflow contract."""

    NODE_TYPES = {"input", "agent", "output"}
    DEFAULT_TIMEOUT_MS = 30_000
    MAX_TIMEOUT_MS = 300_000
    DEFAULT_RETRY_POLICY = {
        "max_attempts": 1,
        "backoff_ms": 250,
        "max_backoff_ms": 5_000,
        "jitter_ms": 250,
        "retryable_error_codes": [
            "NODE_TIMEOUT", "HTTP_429", "HTTP_502", "HTTP_503", "HTTP_504", "CONNECTION_ERROR",
        ],
    }
    CIRCUIT_FAILURE_CODES = {"NODE_TIMEOUT", "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504", "CONNECTION_ERROR"}

    def __init__(self, db: AsyncSession, execution_service=None):
        self.db = db
        self.gateway = ModelGateway()
        self.governance = RuntimeModelGovernanceService(db, gateway=self.gateway)
        self.circuit_breaker = CircuitBreakerService(db)
        self.execution_service = execution_service

    @classmethod
    def validate_timeout_ms(cls, value: object, *, field: str = "timeout_ms") -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(422, f"{field} 必须为整数毫秒")
        if value <= 0 or value > cls.MAX_TIMEOUT_MS:
            raise HTTPException(422, f"{field} 必须在 1-{cls.MAX_TIMEOUT_MS} 毫秒范围内")
        return value

    @classmethod
    def resolve_timeout_ms(cls, config: dict | None, *, field: str = "timeout_ms") -> int:
        config = config or {}
        return cls.validate_timeout_ms(config.get(field, cls.DEFAULT_TIMEOUT_MS), field=field)

    @classmethod
    def resolve_retry_policy(cls, config: dict | None) -> dict:
        config = config or {}
        raw = config.get("retry") or {}
        if not isinstance(raw, dict):
            raise HTTPException(422, "retry config 必须为对象")
        policy = {**cls.DEFAULT_RETRY_POLICY, **raw}
        max_attempts = policy["max_attempts"]
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 5:
            raise HTTPException(422, "retry.max_attempts 必须在 1-5 范围内")
        for key, maximum in (("backoff_ms", 10_000), ("max_backoff_ms", 60_000), ("jitter_ms", 10_000)):
            value = policy[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
                raise HTTPException(422, f"retry.{key} 必须在 0-{maximum} 范围内")
        if policy["max_backoff_ms"] < policy["backoff_ms"]:
            raise HTTPException(422, "retry.max_backoff_ms 不能小于 retry.backoff_ms")
        codes = policy["retryable_error_codes"]
        if not isinstance(codes, list) or any(not isinstance(code, str) or not code for code in codes):
            raise HTTPException(422, "retry.retryable_error_codes 必须为非空字符串数组")
        if len(codes) > 20:
            raise HTTPException(422, "retry.retryable_error_codes 最多允许 20 项")
        return {
            "max_attempts": max_attempts,
            "backoff_ms": policy["backoff_ms"],
            "max_backoff_ms": policy["max_backoff_ms"],
            "jitter_ms": policy["jitter_ms"],
            "retryable_error_codes": codes,
        }
