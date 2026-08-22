import inspect
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution, ExecutionEvent


class ObservabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _add(self, instance: Any) -> None:
        result = self.db.add(instance)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _utc_naive(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

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
        return execution

    async def finish_execution(self, execution: Execution, status: str = "completed", error_code: str | None = None, error_message: str | None = None) -> None:
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
        return str(uuid.uuid4()), str(uuid.uuid4())

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)
