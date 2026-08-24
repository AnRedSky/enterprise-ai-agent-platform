"""Workflow Runtime 熔断器模块。

职责：提供基于数据库持久化状态的 CLOSED/OPEN/HALF_OPEN 熔断状态机与探针配额控制。
边界：只负责 Workflow Runtime 的熔断状态与策略一致性，不负责节点执行、模型 Provider 或 Workflow Service 生命周期。
关键依赖：WorkflowCircuitState ORM、SQLAlchemy AsyncSession 与异步执行上下文。
"""

from __future__ import annotations

from contextvars import ContextVar
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


# 探针完成只能修改为其预留探针的恢复窗口。
# ContextVar 将预留令牌限制在当前异步执行上下文中，避免多个 Runtime 调用共享服务实例时串用探针状态。
_probe_context: ContextVar[tuple[UUID, str, datetime] | None] = ContextVar(
    "workflow_circuit_probe_context", default=None
)


class CircuitBreakerService:
    """数据库持久化的 CLOSED/OPEN/HALF_OPEN 状态机。"""

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
        """构造完整初始化状态，避免依赖 ORM 默认值。"""
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

    @staticmethod
    def _clear_probe_context() -> None:
        _probe_context.set(None)

    @staticmethod
    def _probe_matches(
        tenant_id: UUID,
        circuit_key: str,
        state: WorkflowCircuitState,
    ) -> bool:
        token = _probe_context.get()
        if token is None:
            # 兼容未显式预留探针的直接服务调用；Runtime 调用始终拥有探针令牌。
            return True
        token_tenant, token_key, token_window = token
        return (
            token_tenant == tenant_id
            and token_key == circuit_key
            and state.state == "half_open"
            and state.half_opened_at == token_window
        )

    async def before_call(self, tenant_id: UUID, circuit_key: str, config: dict | None = None) -> str:
        policy = self.validate_config(config)
        self._clear_probe_context()
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
                _probe_context.set((tenant_id, circuit_key, now))
                await self.db.commit()
                return "half_open"
            raise CircuitOpenError(circuit_key)
        if state.state == "half_open":
            if state.success_count >= state.half_open_max_calls:
                raise CircuitOpenError(circuit_key)
            state.success_count += 1
            await self.db.flush()
            _probe_context.set((tenant_id, circuit_key, state.half_opened_at))
            await self.db.commit()
            return "half_open"
        return "closed"

    async def record_success(self, tenant_id: UUID, circuit_key: str, config: dict | None = None) -> None:
        policy = self.validate_config(config)
        if not policy["enabled"]:
            self._clear_probe_context()
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
            self._clear_probe_context()
            return
        self._assert_policy_matches(state, policy)
        if state.state == "half_open":
            if not self._probe_matches(tenant_id, circuit_key, state):
                await self.db.flush()
                self._clear_probe_context()
                return
            state.success_count = max(state.success_count - 1, 0)
            if state.success_count == 0:
                state.state = "closed"
                state.failure_count = 0
                state.opened_at = None
                state.half_opened_at = None
        elif state.state == "closed":
            # 过期 HALF_OPEN 成功事件不得重置新的 CLOSED 窗口。
            token = _probe_context.get()
            if token is None:
                state.failure_count = 0
        await self.db.flush()
        self._clear_probe_context()

    async def record_failure(self, tenant_id: UUID, circuit_key: str, config: dict | None = None) -> str:
        policy = self.validate_config(config)
        if not policy["enabled"]:
            self._clear_probe_context()
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
        if state.state == "half_open" and not self._probe_matches(tenant_id, circuit_key, state):
            await self.db.flush()
            self._clear_probe_context()
            return state.state
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
        self._clear_probe_context()
        return state.state

    def __init__(self, db: AsyncSession):
        self.db = db
