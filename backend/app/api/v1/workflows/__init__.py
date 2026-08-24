"""Workflow API 领域包。

职责：暴露 Workflow 定义、版本、发布及 Trigger 管理接口。
边界：不实现 Workflow 生命周期与 Trigger 业务规则；相关职责统一由领域 Service 负责。
关键依赖：FastAPI、WorkflowRegistry、WorkflowTriggerService 与数据库依赖。
"""
