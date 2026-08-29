"""可观测性领域服务实现。

职责：统一维护 Execution 生命周期、ExecutionEvent 运行事件以及 trace/request 标识，
为 API、Runtime 和其他领域提供一致的运行观测持久化入口。
边界：不负责业务执行、模型调用、工具执行或审计策略；只负责可观测性记录及其数据库持久化。
关键依赖：SQLAlchemy AsyncSession、Execution 与 ExecutionEvent 持久化模型，以及 Agent Runtime Integration Event。
"""

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, User
from app.models.execution import Execution, ExecutionEvent
from app.services.integration.publisher import RuntimeIntegrationEventPublisher


class ObservabilityService:
    """负责记录执行生命周期和执行事件，不承载具体业务执行逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _add(self, instance: Any) -> None:
        """统一兼容同步/异步数据库 Session 的对象添加行为。"""
        result = self.db.add(instance)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _utc_naive(value: datetime | None) -> datetime | None:
        """将带时区时间统一转换为数据库使用的 UTC 无时区时间。"""
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    async def _agent_tenant_id(self, agent_id: UUID | None) -> UUID | None:
        """解析 Agent 所属租户；找不到 Agent 时不制造跨租户事件。"""
        if agent_id is None:
            return None
        result = await self.db.execute(
            select(User.tenant_id)
            .join(Agent, Agent.owner_id == User.id)
            .where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def _publish_agent_event(
        self,
        execution: Execution,
        *,
        event_type: str,
        status: str,
        error_code: str | None = None,
    ) -> None:
        """将 Agent Execution 生命周期映射为统一 Durable Integration Event。"""
        tenant_id = await self._agent_tenant_id(execution.agent_id)
        if tenant_id is None or execution.agent_id is None:
            return
        await RuntimeIntegrationEventPublisher(self.db).publish(
            tenant_id=tenant_id,
            event_type=event_type,
            source=RuntimeIntegrationEventPublisher.SOURCE_AGENT,
            subject=str(execution.id),
            idempotency_key=f"agent-execution:{execution.id}:{status}",
            payload={
                "execution_id": str(execution.id),
                "agent_id": str(execution.agent_id),
                "agent_version": execution.agent_version,
                "model_id": execution.model_id,
                "status": status,
                "error_code": error_code,
            },
            request_id=execution.request_id,
            trace_id=execution.trace_id,
        )

    async def start_execution(
        self,
        request_id: str,
        trace_id: str,
        session_id: UUID | None,
        agent_id: UUID | None,
        agent_version: str | None,
        model_id: str | None,
        model_profile_id: UUID | None = None,
    ) -> Execution:
        """创建并持久化一个运行中的 Execution 记录，并产生 Agent started integration event。"""
        execution = Execution(
            request_id=request_id,
            trace_id=trace_id,
            session_id=session_id,
            agent_id=agent_id,
            agent_version=agent_version,
            model_id=model_id,
            model_profile_id=model_profile_id,
            status="running",
        )
        await self._add(execution)
        await self.db.flush()
        await self._publish_agent_event(
            execution,
            event_type="agent.execution.started",
            status="started",
        )
        return execution

    async def finish_execution(
        self,
        execution: Execution,
        status: str = "completed",
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """完成 Execution 生命周期并计算持续时间及错误信息，同时产生 Agent terminal event。"""
        ended = datetime.now(UTC)
        started = execution.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        execution.status = status
        execution.ended_at = self._utc_naive(ended)
        execution.duration_ms = max(0, int((ended - started).total_seconds() * 1000))
        execution.error_code = error_code
        execution.error_message = error_message
        await self.db.flush()
        if status == "completed":
            event_type = "agent.execution.completed"
        else:
            event_type = "agent.execution.failed"
        await self._publish_agent_event(
            execution,
            event_type=event_type,
            status=status,
            error_code=error_code,
        )

    async def record_event(
        self,
        execution: Execution,
        span_type: str,
        started_at: datetime,
        status: str = "completed",
        model_id: str | None = None,
        model_profile_id: UUID | None = None,
        provider_id: UUID | None = None,
        tool_id: UUID | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionEvent:
        """记录一次 ExecutionEvent，并保存模型、工具、Token 与错误上下文。"""
        ended = datetime.now(UTC)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        event = ExecutionEvent(
            execution_id=execution.id,
            trace_id=execution.trace_id,
            span_type=span_type,
            status=status,
            started_at=self._utc_naive(started_at),
            ended_at=self._utc_naive(ended),
            duration_ms=max(0, int((ended - started_at).total_seconds() * 1000)),
            model_id=model_id,
            model_profile_id=model_profile_id,
            provider_id=provider_id,
            tool_id=tool_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata,
        )
        await self._add(event)
        await self.db.flush()
        return event

    @staticmethod
    def new_ids() -> tuple[str, str]:
        """生成 request_id 与 trace_id，供一次执行建立关联标识。"""
        return str(uuid.uuid4()), str(uuid.uuid4())

    @staticmethod
    def now() -> datetime:
        """返回当前 UTC 时间，作为统一的运行观测时间基准。"""
        return datetime.now(UTC)
