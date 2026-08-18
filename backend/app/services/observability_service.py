import uuid
from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution, ExecutionEvent


class ObservabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_execution(
        self,
        request_id: str,
        trace_id: str,
        session_id: UUID | None,
        agent_id: UUID | None,
        agent_version: str | None,
        model_id: str | None,
    ) -> Execution:
        execution = Execution(
            request_id=request_id,
            trace_id=trace_id,
            session_id=session_id,
            agent_id=agent_id,
            agent_version=agent_version,
            model_id=model_id,
            status="running",
        )
        self.db.add(execution)
        await self.db.flush()
        return execution

    async def finish_execution(
        self,
        execution: Execution,
        status: str = "completed",
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        ended = datetime.now(UTC)
        execution.status = status
        execution.ended_at = ended
        execution.duration_ms = max(0, int((ended - execution.started_at).total_seconds() * 1000))
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
        tool_id: UUID | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> ExecutionEvent:
        ended = datetime.now(UTC)
        event = ExecutionEvent(
            execution_id=execution.id,
            trace_id=execution.trace_id,
            span_type=span_type,
            status=status,
            started_at=started_at,
            ended_at=ended,
            duration_ms=max(0, int((ended - started_at).total_seconds() * 1000)),
            model_id=model_id,
            tool_id=tool_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            error_code=error_code,
            error_message=error_message,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    @staticmethod
    def new_ids() -> tuple[str, str]:
        return str(uuid.uuid4()), str(uuid.uuid4())

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)
