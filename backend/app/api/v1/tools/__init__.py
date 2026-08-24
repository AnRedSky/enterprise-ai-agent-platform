"""Tool API 领域包。

职责：暴露 Tool 管理、绑定与执行接口。
边界：不复制 Tool 权限、审计、可观测性和执行实现；这些职责统一由 Tool Service 负责。
关键依赖：FastAPI、Tool Service、Tool ORM 与数据库依赖。
"""
