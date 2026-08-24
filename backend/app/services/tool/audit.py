"""Tool 审计适配器。

职责：对 Tool 执行成功/失败事件进行敏感字段脱敏并交给统一 Repository 持久化。
边界：不负责 Tool 权限、执行或可观测性；依赖调用方提供 Audit Repository。
"""

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
    """Tool 审计持久化边界。"""

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
            "resource_type": "tool",
            "resource_id": str(context.tool_id),
            "status": "success",
            "metadata_json": sanitize_tool_metadata(metadata or {}),
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
            "resource_type": "tool",
            "resource_id": str(context.tool_id),
            "status": "failure",
            "error_code": getattr(error, "code", "TOOL_EXECUTION_ERROR"),
            "metadata_json": sanitize_tool_metadata(metadata or {}),
        })
