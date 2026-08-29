"""Enterprise Integration 领域正式入口。

职责：暴露事件契约，供业务领域和后续持久化/投递实现复用。
边界：不暴露数据库、HTTP 或消息中间件实现。
"""

from app.services.integration.contract import IntegrationEvent

__all__ = ["IntegrationEvent"]
