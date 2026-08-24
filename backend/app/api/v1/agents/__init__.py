"""Agent API 领域包。

职责：暴露 Agent 创建、版本管理、发布与归档 HTTP 接口。
边界：不实现 Agent 领域规则；业务生命周期统一由 AgentService 负责。
关键依赖：FastAPI、AgentService、Agent ORM 与数据库依赖。
"""
