"""Agent 领域服务入口。

职责：统一暴露 Agent 生命周期与版本管理服务，避免业务层重复实现 Agent 领域规则。
边界：仅负责 Agent 领域服务编排与公共导出，不承载模型供应商、知识检索或运行时执行逻辑。
"""

from app.services.agent.service import AgentService

__all__ = ["AgentService"]
