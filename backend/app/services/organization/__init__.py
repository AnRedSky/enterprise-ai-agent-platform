"""Organization 领域服务公开入口。

职责：统一提供 Organization、Membership 的创建、访问控制、成员治理与 owner transfer 能力。
边界：不重复实现认证、Tenant、Workflow 执行或审计基础设施；审计记录通过统一 AuditLog 模型写入。
关键依赖：Organization / OrganizationMembership / User 模型，以及 SQLAlchemy AsyncSession。
"""

from .service import OrganizationService

__all__ = ["OrganizationService"]
