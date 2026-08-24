"""Tool 领域服务公开入口。

职责：统一暴露 Tool Runtime、权限、审计、可观测性与持久化适配能力。
边界：不负责 API 路由协议适配；底层 HTTP/Schema 技术执行仍由 app.tools 提供。
"""

from .audit import AuditLogAdapter, SENSITIVE_KEYS, sanitize_tool_metadata
from .observability import ToolObservabilityAdapter
from .rbac import ToolRBACService
from .repository import SqlAlchemyAuditRepository, SqlAlchemyToolRepository
from .runtime import ToolExecutionContext, ToolRuntimeService

__all__ = [
    "AuditLogAdapter",
    "SENSITIVE_KEYS",
    "sanitize_tool_metadata",
    "ToolObservabilityAdapter",
    "ToolRBACService",
    "SqlAlchemyAuditRepository",
    "SqlAlchemyToolRepository",
    "ToolExecutionContext",
    "ToolRuntimeService",
]
