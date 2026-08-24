"""Session 领域服务公开入口。

职责：管理 Agent 会话创建、历史消息、运行版本与可用 Model Profile 解析。
边界：不负责 Agent 执行编排、Provider 路由或认证令牌管理。
"""

from .service import SessionService

__all__ = ["SessionService"]
