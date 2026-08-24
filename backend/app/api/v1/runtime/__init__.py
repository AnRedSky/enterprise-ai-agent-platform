"""Runtime 查询 API 领域包。

职责：暴露执行记录、事件、Trace 与审计日志查询接口。
边界：不实现 Runtime 查询业务规则；查询能力统一由 RuntimeQueryService 与 WorkflowExecutionService 承担。
关键依赖：FastAPI、RuntimeQueryService、WorkflowExecutionService 与数据库依赖。
"""
