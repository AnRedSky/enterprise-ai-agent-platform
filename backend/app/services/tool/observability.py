"""Tool 可观测性适配器。

职责：记录 Tool 执行 span 的开始、完成与失败事件。
边界：不负责 Execution 生命周期，也不负责 Tool 业务执行；依赖数据库 Session 持久化 ExecutionEvent。
"""

from datetime import UTC, datetime

from app.models.execution import ExecutionEvent


class ToolObservabilityAdapter:
    """Tool span 持久化适配器。"""

    def __init__(self, db):
        self.db = db
        self.started_at = {}

    def _key(self, context):
        return (context.execution_id, context.tool_id)

    async def start_tool_span(self, context):
        self.started_at[self._key(context)] = datetime.now(UTC)

    async def finish_tool_span(self, context, result):
        await self._record(context, "completed")

    async def fail_tool_span(self, context, error):
        await self._record(context, "failed", getattr(error, "code", "TOOL_EXECUTION_ERROR"), "Tool execution failed")

    async def _record(self, context, status, error_code=None, error_message=None):
        started = self.started_at.pop(self._key(context), datetime.now(UTC))
        ended = datetime.now(UTC)
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
