"""模型 Runtime 入口。

模块职责：提供统一模型调用 Gateway，负责将领域治理结果转换为技术 Provider 调用。
边界：不承担 Provider 路由、组织权限或数据库业务规则；具体外部适配由 infrastructure/providers 提供。
关键外部依赖：ModelGateway 与 infrastructure/providers 中的模型 Contract/Provider。
"""

from .gateway import ModelGateway

__all__ = ["ModelGateway"]
