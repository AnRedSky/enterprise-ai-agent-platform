"""Tool RBAC 领域适配器公开入口。

职责：基于 Agent owner 与 admin role 判断 Tool 执行权限。
边界：不负责 Tool 发现、绑定持久化或实际执行。
"""

from .service import ToolRBACService

__all__ = ["ToolRBACService"]
