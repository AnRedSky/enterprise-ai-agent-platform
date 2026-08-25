"""应用进程入口模块。

职责：集中定义 API、Scheduler 等独立进程的启动编排入口。
边界：不承载领域业务规则；具体执行能力继续由 API、Service、Runtime 与 Infrastructure 提供。
关键依赖：FastAPI 应用与 `ScheduledTriggerScheduler`。
"""
