from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_circuit import WorkflowCircuitState


class CircuitOpenError(HTTPException):
    def __init__(self, circuit_key: str):
        super().__init__(503, f"Circuit breaker is open: {circuit_key}")
        self.circuit_key = circuit_key


class CircuitBreakerService:
    """Database-backed CLOSED/OPEN/HALF_OPEN state machine.

    State is persisted in PostgreSQL so Runtime workers remain stateless and
    circuit state is shared across replicas.
    """

    STATES = {"closed", "open", "half_open"}

    @staticmethod
    def validate_config(config: dict | None) -> dict:
        raw = (config or {}).get("circuit_breaker") or {}
        if not isinstance(raw, dict):
            raise HTTPException(422, "circuit_breaker config 必须为对象")
        enabled = raw.get("enabled", False)
        if not isinstance(enabled, bool):
            raise HTTPException(422, "circuit_breaker.enabled 必须为布尔值")
        threshold = raw.get("failure_threshold", 3)
        recovery_ms = raw.get("recovery_timeout_ms", 10_000)
        half_open_calls = raw.get("half_open_max_calls", 1)
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not 1 <= threshold <= 100:
            raise HTTPException(422, "circuit_breaker.failure_threshold 必须在 1-100 范围内")
        if isinstance(recovery_ms, bool) or not isinstance(recovery_ms, int) or not 100 <= recovery_ms <= 300_000:
            raise HTTPException(422, "circuit_breaker.recovery_timeout_ms 必须在 100-300000 范围内")
        if isinstance(half_open_calls, bool) or not isinstance(half_open_calls, int) or not 1 <= half_open_calls <= 10:
            raise HTTPException(422, "circuit_breaker.half_open_max_calls 必须在 1-10 范围内")
        return {
            "enabled": enabled,
            "failure_threshold": threshold,
            "recovery_timeout_ms": recovery_ms,
            "half_open_max_calls": half_open_calls,
        }

    async def before_call(self, tenant_id: UUID, circuit_key: str, config: dict | None = None) -> str:
        policy = self.validate_config(config)
        if not policy["enabled"]:
            return "closed"
        now = datetime.now(UTC).replace(tzinfo=None)
        result = await self.db.execute(
            select(WorkflowCircuitState)
            .where(
                WorkflowCircuitState.tenant_id == tenant_id,
                WorkflowCircuitState.circuit_key == circuit_key,
            )
            .with_for_update()
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = WorkflowCircuitState(tenant_id=tenant_id, circuit_key=circuit_key)
            self.db.add(state)
            await self.db.flush()
            return "closed"
        if state.state == "open":
            opened_at = state.opened_at or now
            if now - opened_at >= timedelta(milliseconds=policy["recovery_timeout_ms"]):
                state.state = "half_open"
                state.half_opened_at = now
                state.success_count = 0
                await self.db.flush()
                return "half_open"
            raise CircuitOpenError(circuit_key)
        if state.state == "half_open" and state.success_count >= policy["half_open_max_calls"]:
            raise CircuitOpenError(circuit_key)
        return state.state

    async def record_success(self, tenant_id: UUID, circuit_key: str, config: dict | None = None) -> None:
        policy = self.validate_config(config)
        if not policy["enabled"]:
            return
        result = await self.db.execute(
            select(WorkflowCircuitState)
            .where(
                WorkflowCircuitState.tenant_id == tenant_id,
                WorkflowCircuitState.circuit_key == circuit_key,
            )
            .with_for_update()
        )
        state = result.scalar_one_or_none()
        if state is None:
            return
        if state.state == "half_open":
            state.state = "closed"
            state.failure_count = 0
            state.success_count = 0
            state.opened_at = None
            state.half_opened_at = None
        elif state.state == "closed":
            state.failure_count = 0
        await self.db.flush()

    async def record_failure(self, tenant_id: UUID, circuit_key: str, config: dict | None = None) -> str:
        policy = self.validate_config(config)
        if not policy["enabled"]:
            return "closed"
        now = datetime.now(UTC).replace(tzinfo=None)
        result = await self.db.execute(
            select(WorkflowCircuitState)
            .where(
                WorkflowCircuitState.tenant_id == tenant_id,
                WorkflowCircuitState.circuit_key == circuit_key,
            )
            .with_for_update()
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = WorkflowCircuitState(tenant_id=tenant_id, circuit_key=circuit_key)
            self.db.add(state)
            await self.db.flush()
        state.last_failure_at = now
        state.success_count = 0
        if state.state == "half_open" or state.failure_count + 1 >= policy["failure_threshold"]:
            state.state = "open"
            state.failure_count = policy["failure_threshold"]
            state.opened_at = now
            state.half_opened_at = None
        else:
            state.state = "closed"
            state.failure_count += 1
        await self.db.flush()
        return state.state

    def __init__(self, db: AsyncSession):
        self.db = db
