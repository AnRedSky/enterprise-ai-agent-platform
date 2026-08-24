"""Tool Audit 适配器公开入口。

职责：对 Tool 执行成功/失败事件进行敏感字段脱敏并交给统一 Repository 持久化。
边界：不负责 Tool 权限、执行或可观测性。
"""

from .service import AuditLogAdapter, SENSITIVE_KEYS, sanitize_tool_metadata

__all__ = ["AuditLogAdapter", "SENSITIVE_KEYS", "sanitize_tool_metadata"]
