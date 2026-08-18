from dataclasses import dataclass
from typing import Any

from app.tools.exceptions import ToolExecutionError
from app.tools.http_executor import execute_http_tool
from app.tools.schema import validate_object_schema


@dataclass
class ToolExecutionContext:
    actor_id: int
    agent_id: int
    tool_id: int
    execution_id: int | None = None
    trace_id: str | None = None
    request_id: str | None = None


class ToolRuntimeService:
    """Orchestrates registry/binding checks, validation and safe execution.

    Persistence and authorization adapters are intentionally injected so the
    runtime does not couple itself to an API framework or a concrete repository.
    """

    def __init__(self, tool_repository, agent_tool_repository, permission_checker, audit_logger=None, observability=None, max_calls: int = 8):
        self.tool_repository = tool_repository
        self.agent_tool_repository = agent_tool_repository
        self.permission_checker = permission_checker
        self.audit_logger = audit_logger
        self.observability = observability
        self.max_calls = max_calls

    async def execute(self, context: ToolExecutionContext, arguments: dict[str, Any], call_count: int = 0) -> dict[str, Any]:
        if call_count >= self.max_calls:
            raise ToolExecutionError("TOOL_LIMIT_EXCEEDED", "Tool execution limit exceeded")

        tool = await self.tool_repository.get(context.tool_id)
        if tool is None:
            raise ToolExecutionError("TOOL_NOT_FOUND", "Tool not found")
        if not getattr(tool, "is_active", True):
            raise ToolExecutionError("TOOL_DISABLED", "Tool is disabled")

        binding = await self.agent_tool_repository.get_binding(context.agent_id, context.tool_id)
        if binding is None or not getattr(binding, "is_active", True):
            raise ToolExecutionError("TOOL_NOT_BOUND", "Tool is not enabled for this agent")

        allowed = await self.permission_checker(context.actor_id, context.agent_id, context.tool_id)
        if not allowed:
            raise ToolExecutionError("PERMISSION_DENIED", "Tool permission denied")

        validate_object_schema(getattr(tool, "input_schema", {}), arguments)

        if self.observability:
            await self.observability.start_tool_span(context)
        try:
            if getattr(tool, "type", "http") != "http":
                raise ToolExecutionError("UNSUPPORTED_TOOL", "Unsupported tool type")
            result = await execute_http_tool(arguments)
            if self.audit_logger:
                await self.audit_logger.log_success(context, "tool.execute")
            if self.observability:
                await self.observability.finish_tool_span(context, result)
            return result
        except Exception as exc:
            if self.audit_logger:
                await self.audit_logger.log_failure(context, "tool.execute", exc)
            if self.observability:
                await self.observability.fail_tool_span(context, exc)
            raise
