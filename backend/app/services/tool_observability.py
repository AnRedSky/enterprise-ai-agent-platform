from datetime import datetime

from app.models.execution import ExecutionEvent


class ToolObservabilityAdapter:
    def __init__(self, db):
        self.db = db
        self.started_at = {}

    def _key(self, context):
        return (context.execution_id, context.tool_id)

    async def start_tool_span(self, context):
        self.started_at[self._key(context)] = datetime.utcnow()

    async def finish_tool_span(self, context, result):
        await self._record(context, "completed")

    async def fail_tool_span(self, context, error):
        await self._record(context, "failed", getattr(error, "code", "TOOL_EXECUTION_ERROR"), "Tool execution failed")

    async def _record(self, context, status, error_code=None, error_message=None):
        started = self.started_at.pop(self._key(context), datetime.utcnow())
        ended = datetime.utcnow()
        event = ExecutionEvent(
            execution_id=context.execution_id,
            trace_id=context.trace_id or "unknown",
            span_type="tool",
            status=status,
            started_at=started,
            ended_at=ended,
            duration_ms=max(0, int((ended - started).total_seconds() * 1000)),
            tool_id=context.tool_id,
            error_code=error_code,
            error_message=error_message,
        )
        self.db.add(event)
        await self.db.flush()
