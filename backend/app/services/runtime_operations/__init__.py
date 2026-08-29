"""Runtime 运维聚合服务领域包。

职责：提供 Integration Event / Delivery 的运维指标、SLO 计算与死信查询。
边界：只负责只读聚合和运维视图数据，不直接执行 Delivery 网络调用或绕过 Repository 修改状态。
关键依赖：SQLAlchemy AsyncSession，以及 Integration Event / Webhook Delivery 领域模型。
"""

from .service import RuntimeOperationsService

__all__ = ["RuntimeOperationsService"]
