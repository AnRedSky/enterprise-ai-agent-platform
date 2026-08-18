from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {"authorization", "cookie", "set-cookie", "api_key", "apikey", "token", "secret", "password"}


def sanitize_tool_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower().replace("-", "_") in SENSITIVE_KEYS else sanitize_tool_metadata(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_tool_metadata(item) for item in value]
    return value


class AuditLogAdapter:
    """Persistence boundary for tool audit events.

    Concrete DB implementations should persist only sanitized metadata.
    """

    def __init__(self, repository):
        self.repository = repository

    async def log_success(self, context, action: str, metadata: dict | None = None) -> None:
        await self.repository.create({
            "actor_id": context.actor_id,
            "agent_id": context.agent_id,
            "tool_id": context.tool_id,
            "execution_id": context.execution_id,
            "trace_id": context.trace_id,
            "request_id": context.request_id,
            "action": action,
            "status": "success",
            "metadata": sanitize_tool_metadata(metadata or {}),
        })

    async def log_failure(self, context, action: str, error: Exception, metadata: dict | None = None) -> None:
        await self.repository.create({
            "actor_id": context.actor_id,
            "agent_id": context.agent_id,
            "tool_id": context.tool_id,
            "execution_id": context.execution_id,
            "trace_id": context.trace_id,
            "request_id": context.request_id,
            "action": action,
            "status": "failure",
            "error_code": getattr(error, "code", "TOOL_EXECUTION_ERROR"),
            "metadata": sanitize_tool_metadata(metadata or {}),
        })
