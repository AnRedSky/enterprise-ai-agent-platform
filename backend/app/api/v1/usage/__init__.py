"""Usage API 领域包。

职责：暴露模型调用用量与成本查询接口。
边界：不实现计量、成本计算和持久化规则；相关职责统一由 UsageAccountingService 负责。
关键依赖：FastAPI、UsageAccountingService、Usage Schema 与数据库依赖。
"""
