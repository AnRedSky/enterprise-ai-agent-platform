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

    State and the policy that governs that state are persisted in PostgreSQL so
    Runtime workers remain stateless and every caller sharing a circuit key
    observes the same recovery and probe-quota contract.
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
        key = raw.get("key")
        if key is not None and (not isinstance(key, str) or not 1 <= len(key) <= 200):
            raise HTTPException(422, "circuit_breaker.key 必须为 1-200 字符字符串")
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
            "key": key,
            "failure_threshold": threshold,
            "recovery_timeout_ms": recovery_ms,
            "half_open_max_calls": half_open_calls,
        }

    @staticmethod
    def _policy_values(policy: dict) -> tuple[int, int, int]:
        return (
            policy["failure_threshold"],
            policy["recovery_timeout_ms"],
            policy["half_open_max_calls"],
        )

    @classmethod
    def _assert_policy_matches(cls, state: WorkflowCircuitState, policy: dict) -> None:
        persisted = (
            state.failure_threshold,
            state.recovery_timeout_ms,
            state.half_open_max_calls,
        )
        requested = cls._policy_values(policy)
        if persisted != requested:
            raise HTTPException(
                409,
                "Circuit breaker policy mismatch for existing circuit key",
            )

    @staticmethod
    def _new_state(tenant_id: UUID, circuit_key: str, policy: dict) -> WorkflowCircuitState:
        """Build a fully initialized state instead of relying on ORM defaults.

        SQLAlchemy ``default=`` values are applied as INSERT defaults; a newly
        constructed object can still expose ``None`` before the flush. Runtime
        state transitions must never depend on that pre-flush value.
        """
        return WorkflowCircuitState(
            tenant_id=tenant_id,
            circuit_key=circuit_key,
            state="closed",
            failure_threshold=policy["failure_threshold"],
            recovery_timeout_ms=policy["recovery_timeout_ms"],
            half_open_max_calls=policy["half_open_max_calls"],
            failure_count=0,
            success_count=0,
        )

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
            state = self._new_state(tenant_id, circuit_key, policy)
            self.db.add(state)
            await self.db.flush()
            return "closed"

        self._assert_policy_matches(state, policy)
        if state.state == "open":
            opened_at = state.opened_at or now
            if now - opened_at >= timedelta(milliseconds=state.recovery_timeout_ms):
                state.state = "half_open"
                state.half_opened_at = now
                state.success_count = 1
                await self.db.flush()
                # Release the row lock after atomically reserving the first probe.
                # Concurrent callers now observe the consumed HALF_OPEN quota.
                await self.db.commit()
                return "half_open"
            raise CircuitOpenError(circuit_key)
        if state.state == "half_open":
            if state.success_count >= state.half_open_max_calls:
                raise CircuitOpenError(circuit_key)
            # ``success_count`` represents active HALF_OPEN probe reservations.
            # A completed successful probe releases one reservation; the circuit
            # closes only after all reservations from the current recovery window
            # have completed successfully. This prevents a fast success from
            # closing the circuit while another concurrent probe is still running.
            state.success_count += 1
            await self.db.flush()
            await self.db.commit()
            return "half_open"
        return "closed"

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
        self._assert_policy_matches(state, policy)
        if state.state == "half_open":
            # The persisted counter is the number of in-flight HALF_OPEN probes,
            # not the number of successful probes. A success releases its slot.
            # Close only when the recovery window has no outstanding probes.
            state.success_count = max(state.success_count - 1, 0)
            if state.success_count == 0:
                state.state = "closed"
                state.failure_count = 0
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
            state = self._new_state(tenant_id, circuit_key, policy)
            self.db.add(state)
            await self.db.flush()
        else:
            self._assert_policy_matches(state, policy)
        state.last_failure_at = now
        state.success_count = 0
        if state.state == "half_open" or state.failure_count + 1 >= state.failure_threshold:
            state.state = "open"
            state.failure_count = state.failure_threshold
            state.opened_at = now
            state.half_opened_at = None
        else:
            state.state = "closed"
            state.failure_count += 1
        await self.db.flush()
        return state.state

    def __init__(self, db: AsyncSession):
        self.db = db
