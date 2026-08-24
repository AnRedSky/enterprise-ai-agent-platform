"""Model usage accounting 领域服务公开入口。

职责：持久化 Provider 调用用量、价格版本和确定性成本，并提供组织级统计。
边界：不负责 Provider 路由、模型调用或数据库 Session 创建。
"""

from .service import UsageAccountingService

__all__ = ["UsageAccountingService"]
